import math
import os
import time
import threading
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from betfair_scraper import BetfairScraper
from betfair_data import BetfairData

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
DEFAULT_WIDTH = 2
DEFAULT_SIZE = 10
t_end = time.time() + 60

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
    signature_type=2,
    funder=polymarket_address,
)
print("Done!")

market = client.get_market("0xd379496a6146d693c189c36a1ea3170e97bda0fb980cc99917e12cc15898f6c0")
neg_risk = market["neg_risk"]
condition_id = market["condition_id"]
tokens = market["tokens"]
token_ids = [token["token_id"] for token in tokens]

def theo(back, lay):
    return 1 / ((back + lay) / 2)

def exit_market():
    for id in token_ids:
        resp = client.cancel_market_orders(market=condition_id, asset_id=id)
        print(resp)

book_parameters = [BookParams(token_id=token_ids[0], side=BUY), 
                   BookParams(token_id=token_ids[0], side=SELL),
                   BookParams(token_id=token_ids[1], side=BUY), 
                   BookParams(token_id=token_ids[1], side=SELL)]

orders = set()

collateral = client.get_balance_allowance(
        params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
    )
print(collateral)

client.update_balance_allowance(
        params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
)

yes = client.get_balance_allowance(
    params=BalanceAllowanceParams(
        asset_type=AssetType.CONDITIONAL,
        token_id=token_ids[0],
    )
)
print(yes)

no = client.get_balance_allowance(
    params=BalanceAllowanceParams(
        asset_type=AssetType.CONDITIONAL,
        token_id=token_ids[1],
    )
)
print(no)

time.sleep(10) # Wait for the betfair thread to be started
while time.time() < t_end:
    if not betfair_data.data:
        print("Waiting for betfair data")
        time.sleep(1)
        continue
    back_price, lay_price = betfair_data.data["Slovakia"]
    theo_val = theo(back_price, lay_price)
    if 0.03 <= theo_val <= 0.97:
        yes_price = math.floor(100*theo_val - DEFAULT_WIDTH) / 100
        no_price = math.ceil((100*(1-theo_val)) + DEFAULT_WIDTH) / 100
        print(theo_val, yes_price, no_price)
    if not orders:
        resp1 = client.create_and_post_order(OrderArgs(
            price = yes_price,
            size = DEFAULT_SIZE // yes_price,
            side = BUY,
            token_id = token_ids[0]
        ),
        PartialCreateOrderOptions(neg_risk=neg_risk))
        orders.add(resp1)
        resp2 = client.create_and_post_order(OrderArgs(
            price = no_price,
            size = DEFAULT_SIZE // no_price,
            side = BUY,
            token_id = token_ids[1]
        ),
        PartialCreateOrderOptions(neg_risk=neg_risk))
        orders.add(resp2)
        print(resp1)
        print(resp2)

betfair_event.clear()
exit_market()
time.sleep(2)

# next_cursor = "ODcwMA=="
# questions = []

# while next_cursor != "LTE=":
#     markets = client.get_markets(next_cursor)
#     data = markets["data"]
#     for market in data:
#         question = market["question"]
#         questions.append(question)
#         if market["question_id"] == "0x867c1e6d1460e19bdf1995d080928e616f947c0e9d10e65f6ed0a0ebcbaad200":
#             print(market)
#     next_cursor = markets["next_cursor"]

# with open('new_file.txt', 'w', encoding="utf-8") as f:
#     for line in questions:
#         f.write(f"{line}\n")