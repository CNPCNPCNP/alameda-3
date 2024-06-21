import asyncio
import json
import websockets

class MarketSubscriber:
    def __init__(self, token_ids):
        self.token_ids = token_ids
        self.url = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
        self.subscribe_message = {
            "type": "Market",
            "assets_ids": self.token_ids
        }

    async def connect(self):
        async with websockets.connect(self.url) as websocket:
            await self.subscribe(websocket)
            await self.listen(websocket)

    async def subscribe(self, websocket):
        await websocket.send(json.dumps(self.subscribe_message))
        print(f"Subscribed with message: {self.subscribe_message}")

    async def listen(self, websocket):
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                print(f"Received message: {data}")
            except websockets.ConnectionClosed:
                print("Connection closed")
                break

    def run(self):
        try:
            asyncio.run(self.connect())
        except KeyboardInterrupt:
            print("Interrupted by user")