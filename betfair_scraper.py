import time
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException

class BetfairScraper():

    def __init__(self, url: str, username: str, password: str) -> None:
        uc_options = uc.ChromeOptions()
        uc_options.add_experimental_option("prefs", {"credentials_enable_service": False, "profile.password_manager_enabled": False})
                
        self.wd = uc.Chrome(options = uc_options)
        self.wd.maximize_window() # For maximizing window
        self.wd.implicitly_wait(10) # gives an implicit wait for 10 seconds
        self.login(url, username, password)

    def login(self, url, username, password):
        try:
            self.wd.get(url)
            # Try to exit the popup
            try:
                popup = self.wd.find_element(By.XPATH, '//*[@id="modal-content-click-target"]/div[1]/div')
                popup.click_safe()
                time.sleep(1)
            except NoSuchElementException:
                print(f'No popup detected for race at {url}, proceeding cautiously')
                time.sleep(1)

            self.username = self.wd.find_element(By.XPATH, '//*[@id="ssc-liu"]')
            self.password = self.wd.find_element(By.XPATH, '//*[@id="ssc-lipw"]')
            login = self.wd.find_element(By.XPATH, '//*[@id="ssc-lis"]')

            self.username.send_keys(username)
            self.password.send_keys(password)
            login.click_safe()
            time.sleep(5)
        except NoSuchElementException:
            print("Failed login to betfair, retrying")
            self.wd.refresh()
            self.login(url, username, password)
        except ElementClickInterceptedException:
            print("Failed login to betfair, retrying")
            self.wd.refresh()
            self.login(url, username, password)

    def get_prices_soccer(self) -> dict:
        first_name = self.wd.find_element(By.XPATH, 
            '//*[@id="main-wrapper"]/div/div[2]/div/ui-view/div/div/div[1]/div[3]/div/div[1]/div/bf-main-market/bf-main-marketview/div/div[2]/bf-marketview-runners-list[2]/div/div/div/table/tbody/tr[1]/td[1]/div/div[2]/bf-runner-info/div/div/h3').text
        first_back = float(self.wd.find_element(By.XPATH, 
            '//*[@id="main-wrapper"]/div/div[2]/div/ui-view/div/div/div[1]/div[3]/div/div[1]/div/bf-main-market/bf-main-marketview/div/div[2]/bf-marketview-runners-list[2]/div/div/div/table/tbody/tr[1]/td[4]/ours-price-button/button/label[1]').text)
        first_lay = float(self.wd.find_element(By.XPATH, 
            '//*[@id="main-wrapper"]/div/div[2]/div/ui-view/div/div/div[1]/div[3]/div/div[1]/div/bf-main-market/bf-main-marketview/div/div[2]/bf-marketview-runners-list[2]/div/div/div/table/tbody/tr[1]/td[5]/ours-price-button/button/label[1]').text)

        second_name = self.wd.find_element(By.XPATH, 
            '//*[@id="main-wrapper"]/div/div[2]/div/ui-view/div/div/div[1]/div[3]/div/div[1]/div/bf-main-market/bf-main-marketview/div/div[2]/bf-marketview-runners-list[2]/div/div/div/table/tbody/tr[2]/td[1]/div/div[2]/bf-runner-info/div/div/h3').text
        second_back = float(self.wd.find_element(By.XPATH, 
            '//*[@id="main-wrapper"]/div/div[2]/div/ui-view/div/div/div[1]/div[3]/div/div[1]/div/bf-main-market/bf-main-marketview/div/div[2]/bf-marketview-runners-list[2]/div/div/div/table/tbody/tr[2]/td[4]/ours-price-button/button/label[1]').text)
        second_lay = float(self.wd.find_element(By.XPATH, 
            '//*[@id="main-wrapper"]/div/div[2]/div/ui-view/div/div/div[1]/div[3]/div/div[1]/div/bf-main-market/bf-main-marketview/div/div[2]/bf-marketview-runners-list[2]/div/div/div/table/tbody/tr[2]/td[5]/ours-price-button/button/label[1]').text)
        
        draw_back = float(self.wd.find_element(By.XPATH, 
            '//*[@id="main-wrapper"]/div/div[2]/div/ui-view/div/div/div[1]/div[3]/div/div[1]/div/bf-main-market/bf-main-marketview/div/div[2]/bf-marketview-runners-list[2]/div/div/div/table/tbody/tr[3]/td[4]/ours-price-button/button/label[1]').text)
        draw_lay = float(self.wd.find_element(By.XPATH, 
            '//*[@id="main-wrapper"]/div/div[2]/div/ui-view/div/div/div[1]/div[3]/div/div[1]/div/bf-main-market/bf-main-marketview/div/div[2]/bf-marketview-runners-list[2]/div/div/div/table/tbody/tr[3]/td[5]/ours-price-button/button/label[1]').text)
        
        data = {}
        data[first_name] = (first_back, first_lay)
        data[second_name] = (second_back, second_lay)
        data["Draw"] = (draw_back, draw_lay)
        return data

    def refresh(self) -> None:
        refresh_button = self.wd.find_element(By.CLASS_NAME, 'refresh-btn')
        refresh_button.click_safe()

    def close(self) -> None:
        self.wd.close()