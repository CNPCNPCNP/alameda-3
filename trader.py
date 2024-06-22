import asyncio
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

        first_orders = OpenOrders()
        second_orders = OpenOrders()
        draw_orders = OpenOrders()

        first_position = Position()
        second_position = Position()
        draw_position = Position()

        self.orders = [first_orders, second_orders, draw_orders]
        self.positions = [first_position, second_position, draw_position]

    async def make_markets(self):
        while not self.stop_event.is_set():
            try:
                message = self.message_queue.get_nowait()
                print(f"Processing message: {message}")
                print(type(message))
            except asyncio.QueueEmpty:
                # No message received, do other stuff without blocking
                self.check_current_orders()
                await asyncio.sleep(0.5)
        print("Exiting all trades!")
        self.exit_market()

    def check_current_orders(self):
        if not self.betfair_data.data:
            print("Waiting for betfair data")
            return
        for index, (open_orders, market) in enumerate(zip(self.orders, self.markets)):
            back, lay = self.betfair_data.data[TEAMS[index]]
            theoval = theo(back, lay)
            if theoval < 0.03 or theoval > 0.97:
                print("Theoval too skewed, not trading")
                return
            
            token_ids = [token["token_id"] for token in market["tokens"]]
            neg_risk = market["neg_risk"]

            if open_orders.yes_sent_vol + open_orders.yes_confirmed_vol <= 0:
                open_orders.yes_price = math.floor(100*theoval - DEFAULT_WIDTH) / 100
                print(f"Buying Yes for {TEAMS[index]}, {theoval}, @ {open_orders.yes_price}")
                resp = self.client.create_and_post_order(OrderArgs(
                    price = open_orders.yes_price,
                    size = max(5, DEFAULT_SIZE // open_orders.yes_price),
                    side = BUY,
                    token_id=token_ids[0]
                ),
                PartialCreateOrderOptions(neg_risk=neg_risk))
                print(resp)
                open_orders.yes_sent_vol += DEFAULT_SIZE
            if open_orders.no_sent_vol + open_orders.no_confirmed_vol <= 0:
                open_orders.no_price = math.ceil((100*(1-theoval)) - DEFAULT_WIDTH) / 100
                print(f"Buying No for {TEAMS[index]}, {theoval}, @ {open_orders.no_price}")
                resp = self.client.create_and_post_order(OrderArgs(
                    price = open_orders.no_price,
                    size = max(5, DEFAULT_SIZE // open_orders.no_price),
                    side = BUY,
                    token_id=token_ids[1]
                ),
                PartialCreateOrderOptions(neg_risk=neg_risk))
                print(resp)
                open_orders.no_sent_vol += DEFAULT_SIZE
            
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