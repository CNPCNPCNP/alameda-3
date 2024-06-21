import os
import time
import threading
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException\

from betfair_scraper import BetfairScraper

from py_clob_client.constants import POLYGON
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from py_clob_client.order_builder.constants import BUY

host = "https://clob.polymarket.com"
key = os.getenv("PK")
username = os.getenv("BETFAIR_USERNAME")
password = os.getenv("BETFAIR_PASSWORD")
chain_id = POLYGON

match_url = "https://www.betfair.com.au/exchange/plus/football/market/1.229548287"

# # Create CLOB client and get/set API credentials
# client = ClobClient(host, key=key, chain_id=chain_id)
# client.set_api_creds(client.create_or_derive_api_creds())

def start_betfair_thread(match_url):
    t_end = time.time() + 45
    scraper = BetfairScraper(match_url, username, password)
    while time.time() < t_end:
        books = scraper.get_prices_soccer()
        time.sleep(0.5)
    scraper.close()
    time.sleep(1)
    return

betfair_thread = threading.Thread(target = start_betfair_thread, args = [match_url])
betfair_thread.start()


