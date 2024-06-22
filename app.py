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

BETFAIR_URL = "https://www.betfair.com.au/exchange/plus/football/market/1.229546023"
FIRST_SLUG = "will-turkey-win-june-22"
SECOND_SLUG = "will-portugal-win-june-22"
DRAW_SLUG = "will-the-match-be-a-draw-Turkey-portugal"

host = "https://clob.polymarket.com"
key = os.getenv("PK")
polymarket_address = os.getenv("ADDRESS")
username = os.getenv("BETFAIR_USERNAME")
password = os.getenv("BETFAIR_PASSWORD")
chain_id = POLYGON

betfair_data = BetfairData([])

def start_betfair_thread(match_url, betfair_data, betfair_event):
    scraper = BetfairScraper(match_url, username, password)
    while betfair_event.is_set():
        betfair_data.data = scraper.get_prices_soccer()
        time.sleep(0.5)
    scraper.close()
    time.sleep(1)
    return

async def main(client, markets, creds, betfair_event, betfair_data):
    message_queue = asyncio.Queue()
    stop_event = asyncio.Event()
    
    subscriber = MarketSubscriber([market["condition_id"] for market in markets], 
                                  creds, 
                                  message_queue, 
                                  stop_event)
    trader = Trader(client, message_queue, markets, betfair_data, stop_event)

    subscriber_task = asyncio.create_task(subscriber.run())
    app_task = asyncio.create_task(trader.make_markets())
    print("Tasks started")

    await asyncio.sleep(60)
    print("Timer expired. Disconnecting...")
    subscriber.stop_event.set()
    trader.stop_event.set()
    betfair_event.clear()
    
    await subscriber_task
    await app_task
    

if __name__ == "__main__":
    client = ClobClient(host, key=key, chain_id=chain_id)
    creds = client.create_or_derive_api_creds()
    client = ClobClient(
        host,
        key=key,
        chain_id=chain_id,
        creds=creds,
        funder=polymarket_address,
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