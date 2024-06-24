import asyncio
from functools import partial
import math

from order import Order
from market_details import MarketDetails

from py_clob_client.constants import POLYGON
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, PartialCreateOrderOptions
from py_clob_client.order_builder.constants import BUY, SELL

DEFAULT_WIDTH = 1
DEFAULT_SIZE = 5
MAKER = "MAKER"
TAKER= "TAKER"
YES = "YES"
NO = "NO"

def theo(back, lay):
    return 1 / ((back + lay) / 2)

class Trader():
    def __init__(self, client, message_queue, markets, betfair_data, stop_event, teams):
        self.client = client
        self.message_queue = message_queue
        self.markets = markets
        self.betfair_data = betfair_data
        self.teams = teams
        self.stop_event = stop_event
        
        self.market_details = []
        for index, market in enumerate(markets):
            market_id = market["condition_id"]
            neg_risk = market["neg_risk"]
            token_ids = [token["token_id"] for token in market["tokens"]]
            market_detail = MarketDetails(self.teams[index], market_id, token_ids[0], token_ids[1], neg_risk)
            self.market_details.append(market_detail)

    async def make_markets(self, subscription_complete_event):
        await subscription_complete_event.wait()
        while not self.stop_event.is_set():
            try:
                message = self.message_queue.get_nowait()
                if message["type"] == "PLACEMENT":
                    self.handle_placement_message(message)
                if message["type"] == "CANCELLATION":
                    self.handle_cancel_message(message)
                if message["type"] == "TRADE":
                    self.handle_trade_message(message)
                await self.check_current_orders()
            except asyncio.QueueEmpty:
                # No message received, do other stuff without blocking
                await self.check_current_orders()
                await asyncio.sleep(0.5)
        print("Exiting all trades!")
        self.exit_market()

    def handle_placement_message(self, message):
        market_id = message["market"]
        token_id = message["asset_id"]
        order_id = message["id"]
        for market_detail in self.market_details:
            if market_detail.market_id == market_id:
                if market_detail.yes_token == token_id:
                    print(f"Order {order_id} successfully placed in {market_detail.market_name} on YES")
                if market_detail.no_token == token_id:
                    print(f"Order {order_id} successfully placed in {market_detail.market_name} on NO")


    def handle_cancel_message(self, message):
        market_id = message["market"]
        token_id = message["asset_id"]
        order_id = message["id"]
        print("Handling a cancel message!")
        for market_detail in self.market_details:
            if market_detail.market_id == market_id:
                if market_detail.yes_token == token_id:
                    if order_id in market_detail.yes_sent_orders:
                        del market_detail.yes_sent_orders[order_id]
                    print(market_detail.yes_sent_orders)
                if market_detail.no_token == token_id:
                    if order_id in market_detail.no_sent_orders:
                        del market_detail.no_sent_orders[order_id]
                    print(market_detail.no_sent_orders)

    def handle_trade_message(self, message):
        market_id = message["market"]
        maker_orders = message["maker_orders"][0]
        side = message["trader_side"]
        if message["status"] != "MATCHED":
            return
        print(message)
        
        if side == MAKER:
            token_id = maker_orders["asset_id"]
            filled = float(maker_orders["matched_amount"])
            price = float(maker_orders["price"])
            order_id = maker_orders["order_id"]
        if side == TAKER:
            token_id = message["asset_id"]
            filled = float(message["size"])
            price = float(message["price"])
            order_id = message["taker_order_id"]	
        for market_detail in self.market_details:
            if market_detail.market_id == market_id:
                if market_detail.yes_token == token_id:
                    order = market_detail.yes_sent_orders[order_id]
                    market_detail.yes_position += filled
                    print(f"Traded Yes @ {price} for {filled} in {market_detail.market_name}. Theoval {market_detail.theoval}")
                    order.size -= filled
                    if order.size <= 0:
                        print("Order fully filled, removing")
                        del market_detail.yes_sent_orders[order_id]                      
                if market_detail.no_token == token_id:
                    order = market_detail.no_sent_orders[order_id]
                    market_detail.no_position += filled
                    print(f"Traded No @ {price} for {filled} in {market_detail.market_name}. Theoval {market_detail.theoval}")
                    order.size -= filled
                    if order.size <= 0:
                        print("Order fully filled, removing")
                        del market_detail.no_sent_orders[order_id]
                print(f"New position: {market_detail.yes_position}, {market_detail.no_position}")
        
    async def check_current_orders(self):
        if not self.betfair_data.data:
            print("Waiting for betfair data")
            return
        for index, market_detail in enumerate(self.market_details):
            back, lay = self.betfair_data.data[self.teams[index]]
            theoval = theo(back, lay)
            if theoval < 0.04 or theoval > 0.96:
                print("Theoval too skewed, not trading")
                return

            yes_price = math.floor(100*theoval - DEFAULT_WIDTH) / 100
            no_price = math.ceil((100*(1-theoval)) - DEFAULT_WIDTH) / 100
            if market_detail.yes_position >= market_detail.no_position + 5:
                yes_price -= 0.01
                no_price += 0.01
            if market_detail.yes_position + 5 <= market_detail.no_position:
                yes_price += 0.01
                no_price -= 0.01
            
            market_detail.theoval = theoval
            market_detail.yes_price = yes_price
            market_detail.no_price = no_price

            self.remove_bad_orders(market_detail, yes_price, no_price)

            await self.check_and_send_if_new_order_needed(market_detail, yes_price, YES)
            await self.check_and_send_if_new_order_needed(market_detail, no_price, NO)
            await self.check_and_send_if_new_order_needed(market_detail, yes_price - 0.01, YES)
            await self.check_and_send_if_new_order_needed(market_detail, no_price - 0.01, NO)
            await self.check_and_send_if_new_order_needed(market_detail, yes_price - 0.02, YES)
            await self.check_and_send_if_new_order_needed(market_detail, no_price - 0.02, NO)

            

    async def check_and_send_if_new_order_needed(self, market_detail, price, side):
        if side == YES:
            sent_orders = market_detail.yes_sent_orders
            token = market_detail.yes_token
            if market_detail.yes_position > market_detail.no_position + 10:
                return False
        else:
            sent_orders = market_detail.no_sent_orders
            token = market_detail.no_token
            if market_detail.no_position > market_detail.yes_position + 10:
                return False

        for order_id in sent_orders:
            order = sent_orders[order_id]
            if order.price == price:
                return False
        
        print(f"Buying {side} for {market_detail.market_name}, {market_detail.theoval}, @ {price}")
        await self.send_buy_order(market_detail,
                                    price,
                                    DEFAULT_SIZE,
                                    side,
                                    token,
                                    market_detail.neg_risk,
                                    market_detail.theoval)
                
    def remove_bad_orders(self, market, yes_price, no_price):
        self.remove_bad_orders_helper(market, market.yes_sent_orders, yes_price)
        self.remove_bad_orders_helper(market, market.no_sent_orders, no_price)

    def remove_bad_orders_helper(self, market, orders, cancellation_price):
        for order_id in orders:
            order = orders[order_id]
            if order.price > cancellation_price:
                print(
                    f"Should remove bad orders from YES above {cancellation_price} in market {market.market_name}, theoval {market.theoval}")
                resp = self.client.cancel(order_id)
                if resp["not_canceled"]:
                    print("Order already cancelled")
                    del orders[order_id]
                    print(orders)

    async def send_buy_order(self, market, price, size, side, token, neg_risk, theoval):
        resp = await self.create_and_post_order_async(price,
                                                      size,
                                                      BUY,
                                                      token,
                                                      neg_risk)
        print(resp)
        
        order = Order(resp["orderID"], 
                        token,
                        side, 
                        DEFAULT_SIZE, 
                        price, 
                        theoval)
        if side == YES:
            market.yes_sent_orders[resp["orderID"]] = order
        else:
            market.no_sent_orders[resp["orderID"]] = order

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