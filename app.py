import asyncio
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
from market_subscriber import MarketSubscriber
from trader import Trader

from py_clob_client.constants import POLYGON
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import AssetType, BalanceAllowanceParams, BookParams, OrderArgs, PartialCreateOrderOptions
from py_clob_client.order_builder.constants import BUY, SELL

BETFAIR_URL = "https://www.betfair.com.au/exchange/plus/football/market/1.229545294"
FIRST_SLUG = "will-the-netherlands-win-June-25"
SECOND_SLUG = "will-austria-win-june-25"
DRAW_SLUG = "will-the-match-be-a-draw-netherlands-austria"
TEAMS = ["Netherlands", "Austria", "Draw"]
RUNTIME = 22800

HOST = "https://clob.polymarket.com"
KEY = os.getenv("PK")
POLYMARKET_ADDRESS = os.getenv("ADDRESS")
USERNAME = os.getenv("BETFAIR_USERNAME")
PASSWORD = os.getenv("BETFAIR_PASSWORD")
CHAIN_ID = POLYGON

betfair_data = BetfairData([])

def start_betfair_thread(match_url, betfair_data, betfair_event):
    scraper = BetfairScraper(match_url, USERNAME, PASSWORD)
    while betfair_event.is_set():
        betfair_data.data = scraper.get_prices_soccer()
        time.sleep(0.5)
    scraper.close()
    time.sleep(1)
    return 

async def shutdown_after_delay(delay, stop_event):
    await asyncio.sleep(delay)
    print("Timer expired. Initiating shutdown...")
    stop_event.set()

async def main(client, markets, creds, betfair_event, betfair_data):
    message_queue = asyncio.Queue()
    stop_event = asyncio.Event()
    subscription_complete_event = asyncio.Event()
    
    subscriber = MarketSubscriber([market["condition_id"] for market in markets], 
                                  creds, 
                                  message_queue, 
                                  stop_event,
                                  subscription_complete_event)
    trader = Trader(client, 
                    message_queue, 
                    markets, 
                    betfair_data, 
                    stop_event,
                    TEAMS,
                    POLYMARKET_ADDRESS)

    subscriber_task = asyncio.create_task(subscriber.run())
    consumer_task = asyncio.create_task(trader.process_messages())
    shutdown_task = asyncio.create_task(shutdown_after_delay(RUNTIME, stop_event))
    print("Tasks started")

    await trader.make_markets(subscription_complete_event)
    betfair_event.clear()
    print("Exiting all trades!")
    trader.exit_market()
    
    await subscriber_task
    await consumer_task
    await shutdown_task

if __name__ == "__main__":
    client = ClobClient(HOST, key=KEY, chain_id=CHAIN_ID)
    creds = client.create_or_derive_api_creds()
    client = ClobClient(
        HOST,
        key=KEY,
        chain_id=CHAIN_ID,
        creds=creds,
        funder=POLYMARKET_ADDRESS,
        signature_type=2
    )
    print("Done!")

    betfair_event = threading.Event()
    betfair_event.set()
    betfair_thread = threading.Thread(target = start_betfair_thread, args = [BETFAIR_URL, betfair_data, betfair_event])
    betfair_thread.start()

    #Give some time for the betfair thread to start
    time.sleep(15)
    get_market_ids = GetMarketId(client, FIRST_SLUG, SECOND_SLUG, DRAW_SLUG)
    ids = get_market_ids.get_market_ids()
    markets = [client.get_market(id) for id in ids]
    
    asyncio.run(main(client, markets, creds, betfair_event, betfair_data))