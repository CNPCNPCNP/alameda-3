import math
import os
import time
import threading
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from betfair_scraper import BetfairScraper
from betfair_data import BetfairData
from get_market_id import GetMarketId

from py_clob_client.constants import POLYGON
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import AssetType, BalanceAllowanceParams, BookParams, OrderArgs, PartialCreateOrderOptions
from py_clob_client.order_builder.constants import BUY, SELL

host = "https://clob.polymarket.com"
key = os.getenv("PK")
polymarket_address = os.getenv("ADDRESS")
username = os.getenv("BETFAIR_USERNAME")
password = os.getenv("BETFAIR_PASSWORD")
chain_id = POLYGON

match_url = "https://www.betfair.com.au/exchange/plus/football/market/1.229548287"

betfair_data = BetfairData([])
FIRST_SLUG = "will-slovakia-win-jun-21"
SECOND_SLUG = "will-ukraine-win-jun-21"
DRAW_SLUG = "will-the-match-be-a-draw-slovakia-ukraine"
DEFAULT_WIDTH = 1
DEFAULT_SIZE = 5
t_end = time.time() + 90

def start_betfair_thread(match_url, betfair_data, betfair_event):
    scraper = BetfairScraper(match_url, username, password)
    while betfair_event.is_set():
        betfair_data.data = scraper.get_prices_soccer()
        time.sleep(0.5)
    scraper.close()
    time.sleep(1)
    return

betfair_event = threading.Event()
betfair_event.set()
betfair_thread = threading.Thread(target = start_betfair_thread, args = [match_url, betfair_data, betfair_event])
betfair_thread.start()

# Create CLOB client and get/set API credentials
client = ClobClient(host, key=key, chain_id=chain_id)
client = ClobClient(
    host,
    key=key,
    chain_id=chain_id,
    creds=client.create_or_derive_api_creds(),
    funder=polymarket_address,
    signature_type=2
)
print("Done!")

get_market_ids = GetMarketId(client, FIRST_SLUG, SECOND_SLUG, DRAW_SLUG)
ids = get_market_ids.get_market_ids()

markets = []
for id in ids:
    markets.append(client.get_market(id))

def theo(back, lay):
    return 1 / ((back + lay) / 2)

def exit_market():
    for market in markets:
        condition_id = market["condition_id"]
        token_ids = [token["token_id"] for token in market["tokens"]]
        for id in token_ids:
            resp = client.cancel_market_orders(market=condition_id, asset_id=id)
            print(resp)

def create_book_parameters(token_ids):
    return [BookParams(token_id=token_ids[0], side=BUY), 
            BookParams(token_id=token_ids[0], side=SELL),
            BookParams(token_id=token_ids[1], side=BUY), 
            BookParams(token_id=token_ids[1], side=SELL)]

orders = {}
time.sleep(10) # Wait for the betfair thread to be started
while time.time() < t_end:
    if not betfair_data.data:
        print("Waiting for betfair data")
        time.sleep(1)
        continue
    for index, market in enumerate(markets):
        token_ids = [token["token_id"] for token in market["tokens"]]
        neg_risk = market["neg_risk"]

        if index == 0:
            market_name = "Slovakia"
        elif index == 1:
            market_name = "Ukraine"
        else:
            market_name = "Draw"

        back_price, lay_price = betfair_data.data[market_name]
        theo_val = theo(back_price, lay_price)

        if 0.03 <= theo_val <= 0.97:
            yes_price = math.floor(100*theo_val - DEFAULT_WIDTH) / 100
            no_price = math.ceil((100*(1-theo_val)) - DEFAULT_WIDTH) / 100
            print(market_name, theo_val, yes_price, no_price)
        if market_name not in orders:
            resp1 = client.create_and_post_order(OrderArgs(
                price = yes_price,
                size = max(5, DEFAULT_SIZE // yes_price),
                side = BUY,
                token_id=token_ids[0]
            ),
            PartialCreateOrderOptions(neg_risk=neg_risk))
            resp2 = client.create_and_post_order(OrderArgs(
                price = no_price,
                size = max(5, DEFAULT_SIZE // no_price),
                side = BUY,
                token_id = token_ids[1]
            ),
            PartialCreateOrderOptions(neg_risk=neg_risk))
            orders[market_name] = [resp1["orderID"], resp2["orderID"]]
            print(resp1)
            print(resp2)
    time.sleep(0.5)

betfair_event.clear()
exit_market()
time.sleep(2)