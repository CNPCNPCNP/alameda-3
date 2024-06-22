import asyncio
from functools import partial
import math

from open_orders import OpenOrders
from position import Position

from py_clob_client.constants import POLYGON
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import AssetType, BalanceAllowanceParams, BookParams, OrderArgs, PartialCreateOrderOptions
from py_clob_client.order_builder.constants import BUY, SELL

DEFAULT_WIDTH = 1
DEFAULT_SIZE = 5
TEAMS = ["Turkey", "Portugal", "Draw"]

def theo(back, lay):
    return 1 / ((back + lay) / 2)

class Trader():
    def __init__(self, client, message_queue, markets, betfair_data, stop_event):
        self.client = client
        self.message_queue = message_queue
        self.markets = markets
        self.betfair_data = betfair_data
        self.stop_event = stop_event
        
        self.orders = []
        self.positions = []
        for market in markets:
            market_id = market["condition_id"]
            neg_risk = market["neg_risk"]
            token_ids = [token["token_id"] for token in market["tokens"]]
            order = OpenOrders(market_id, token_ids[0], token_ids[1], neg_risk)
            position = Position(market_id, token_ids[0], token_ids[1], neg_risk)
            self.orders.append(order)
            self.positions.append(position)

    async def make_markets(self, subscription_complete_event):
        await subscription_complete_event.wait()
        while not self.stop_event.is_set():
            try:
                message = self.message_queue.get_nowait()
                if message["type"] == "PLACEMENT":
                    market_id = message["market"]
                    filled = int(message["size_matched"])
                    newly_open = int(message["original_size"]) - filled
                    token_id = message["asset_id"]
                    for order in self.orders:
                        if order.market_id == market_id:
                            if order.yes_token == token_id:
                                order.yes_confirmed_vol += newly_open
                                order.yes_sent_vol -= newly_open
                            if order.no_token == token_id:
                                order.no_confirmed_vol += newly_open
                                order.no_sent_vol -= newly_open
                await self.check_current_orders()
            except asyncio.QueueEmpty:
                # No message received, do other stuff without blocking
                await self.check_current_orders()
                await asyncio.sleep(0.5)
        print("Exiting all trades!")
        self.exit_market()

    async def check_current_orders(self):
        if not self.betfair_data.data:
            print("Waiting for betfair data")
            return
        for index, open_orders in enumerate(self.orders):
            back, lay = self.betfair_data.data[TEAMS[index]]
            theoval = theo(back, lay)
            if theoval < 0.03 or theoval > 0.97:
                print("Theoval too skewed, not trading")
                return
    
            if open_orders.yes_sent_vol + open_orders.yes_confirmed_vol <= 0:
                open_orders.yes_price = math.floor(100*theoval - DEFAULT_WIDTH) / 100
                open_orders.yes_sent_vol += DEFAULT_SIZE
                print(f"Buying Yes for {TEAMS[index]}, {theoval}, @ {open_orders.yes_price}")
                
                resp = await self.create_and_post_order_async(open_orders.yes_price,
                                                              DEFAULT_SIZE,
                                                              BUY,
                                                              open_orders.yes_token,
                                                              open_orders.neg_risk)
                print(resp)
            if open_orders.no_sent_vol + open_orders.no_confirmed_vol <= 0:
                open_orders.no_price = math.ceil((100*(1-theoval)) - DEFAULT_WIDTH) / 100
                open_orders.no_sent_vol += DEFAULT_SIZE
                print(f"Buying No for {TEAMS[index]}, {theoval}, @ {open_orders.no_price}")

                resp = await self.create_and_post_order_async(open_orders.no_price,
                                                              DEFAULT_SIZE,
                                                              BUY,
                                                              open_orders.no_token,
                                                              open_orders.neg_risk)
                print(resp)

    async def create_and_post_order_async(self, price, size, side, token_id, neg_risk):
        loop = asyncio.get_running_loop()

        func = partial(
            self.client.create_and_post_order,
            OrderArgs(
                price=price,
                size=size,
                side=side,
                token_id=token_id
            ),
            PartialCreateOrderOptions(neg_risk=neg_risk)
        )
        response = await loop.run_in_executor(None, func)
        return response
            
    def exit_market(self):
        for market in self.markets:
            condition_id = market["condition_id"]
            token_ids = [token["token_id"] for token in market["tokens"]]
            for id in token_ids:
                resp = self.client.cancel_market_orders(market=condition_id, asset_id=id)
                print(resp)    

#         if 0.03 <= theo_val <= 0.97:
#             yes_price = math.floor(100*theo_val - DEFAULT_WIDTH) / 100
#             no_price = math.ceil((100*(1-theo_val)) - DEFAULT_WIDTH) / 100
#             print(market_name, theo_val, yes_price, no_price)
#         if market_name not in orders:
#             resp1 = client.create_and_post_order(OrderArgs(
#                 price = yes_price,
#                 size = max(5, DEFAULT_SIZE // yes_price),
#                 side = BUY,
#                 token_id=token_ids[0]
#             ),
#             PartialCreateOrderOptions(neg_risk=neg_risk))
#             resp2 = client.create_and_post_order(OrderArgs(
#                 price = no_price,
#                 size = max(5, DEFAULT_SIZE // no_price),
#                 side = BUY,
#                 token_id = token_ids[1]
#             ),
#             PartialCreateOrderOptions(neg_risk=neg_risk))
#             orders[market_name] = [resp1["orderID"], resp2["orderID"]]
#             print(resp1)
#             print(resp2)
#     time.sleep(0.5)