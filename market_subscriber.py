import asyncio
import json
import websockets

class MarketSubscriber:
    def __init__(self, markets, creds, message_queue, stop_event, subscription_complete_event):
        self.markets = markets
        self.creds = creds
        self.url = "wss://ws-subscriptions-clob.polymarket.com/ws/user"
        self.message_queue = message_queue
        self.subscribe_message = self.create_subscription_message()
        self.stop_event = stop_event
        self.subscription_complete_event = subscription_complete_event

    def create_subscription_message(self):
        auth = {
            "apiKey": self.creds.api_key,
            "secret": self.creds.api_secret,
            "passphrase": self.creds.api_passphrase,
        }

        subscription_message = {
            "auth": auth,
            "type": "User",
            "markets": self.markets,
        }

        return subscription_message

    async def connect(self):
        async with websockets.connect(self.url) as websocket:
            await self.subscribe(websocket)
            await self.listen(websocket)

    async def subscribe(self, websocket):
        await websocket.send(json.dumps(self.subscribe_message))
        print(f"Subscribed with message: {self.subscribe_message}")
        self.subscription_complete_event.set()

    async def listen(self, websocket):
        while not self.stop_event.is_set():
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                data = json.loads(message)
                await self.message_queue.put(data)
            except asyncio.TimeoutError:
                continue
            except websockets.ConnectionClosed:
                print("Connection closed, will retry")
                await self.handle_reconnect()
                return
        print("exiting market subscriber normally")
        await websocket.close()

    async def handle_reconnect(self):
        backoff_time = 1
        while not self.stop_event.is_set():
            print(f"Attempting to reconnect in {backoff_time} seconds...")
            await asyncio.sleep(backoff_time)
            backoff_time = min(backoff_time * 2, 60)  # Exponential backoff with a maximum of 60 seconds
            try:
                async with websockets.connect(self.url) as websocket:
                    await self.subscribe(websocket)
                    await self.listen(websocket)
                    return
            except Exception as e:
                print(f"Reconnection failed: {e}")

    async def run(self):
        await self.connect()