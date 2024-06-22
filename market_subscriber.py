import asyncio
import json
import websockets

class MarketSubscriber:
    def __init__(self, markets, creds, message_queue, stop_event):
        self.markets = markets
        self.creds = creds
        self.url = "wss://ws-subscriptions-clob.polymarket.com/ws/user"
        self.message_queue = message_queue
        self.subscribe_message = self.create_subscription_message()
        self.stop_event = stop_event

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

    async def listen(self, websocket):
        while not self.stop_event.is_set():
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                data = json.loads(message)
                await self.message_queue.put(data)
            except asyncio.TimeoutError:
                continue
            except websockets.ConnectionClosed:
                print("Connection closed")
                break
        print("exiting market subscriber")
        await websocket.close()

    async def run(self):
        await self.connect()