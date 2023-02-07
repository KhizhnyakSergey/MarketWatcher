import time, re
# from selenium import webdriver
import undetected_chromedriver as webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from telethon import TelegramClient
import asyncio
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import json
from functools import reduce

url = 'https://hstock.org/store/tgacc-5322f8bb'
# test link
# url = 'https://hstock.org/store/telegram-pride-5e00c1f5' 


async def notify():
    client = TelegramClient('+4123456789', 1, '1')
    try:
        await client.connect()
        await client.send_message('nickname', f'Accounts on {url} available!!!')
    except BaseException as e: 
        print(e)
    finally: 
        await client.disconnect()

def auth():
    browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), use_subprocess=True, headless=False)
    browser.get(url)
    browser.maximize_window()
    browser.implicitly_wait(10)
    # money = WebDriverWait(browser, 2).until(lambda driver: driver.find_element(By.CSS_SELECTOR, 'span.profile-user_info__walet-text > span.inline'))
    # print(money.text)
    input('Save session')
    # browser.quit()

    with open('hstock_session.json', 'w', encoding='utf-8') as file:
        json.dump(browser.get_cookies(), file, indent=4)
    
    browser.close()
    browser.quit()


def check_product():

    browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), use_subprocess=True, headless=True)
    browser.get(url)
    browser.maximize_window()
    browser.implicitly_wait(10)

    with open('hstock_session.json', 'r') as file:
        cookies = json.load(file)
    for cookie in cookies:
        browser.add_cookie(cookie)
    browser.refresh()

    try:
        WebDriverWait(browser, 10).until(lambda driver: driver.find_element(By.CSS_SELECTOR, 'span.profile-user_info__walet-text > span.inline'))
    except TimeoutException:
        print('Обновите сессию')

    count = 1
    delay = 15
    while True:
        try:
            no_products = True
            try:
                WebDriverWait(browser, 2).until(EC.presence_of_element_located((By.CLASS_NAME, 'profileList__no-products')))
            except TimeoutException: 
                no_products = False
            if no_products: 
                print(f'#{count} No phones')
            else:
                WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.CLASS_NAME, 'swiper-wrapper')))
                products = browser.find_element(By.CLASS_NAME, 'swiper-wrapper')
                product_list = products.find_elements(By.CLASS_NAME, 'profileList-card__name')

                indonesian = []
                for product in product_list:
                    if 'Indonesia' in product.text: indonesian.append(True) 
                    else: indonesian.append(False)    
                if all(indonesian): 
                    print(f'#{count} Only indonesian accounts available')
                else:
                    print(f'#{count} Accounts available! Sending notification...')
                    return browser
        except TimeoutException:
            print('TIMEOUT')
        finally:
            browser.refresh()
        count += 1


async def buy_product(browser: WebDriver):
    sings_to_remove = ((' ', ''), (',', '.'), ('шт', ''), ('₽', ''))
    
    money = WebDriverWait(browser, 10).until(lambda driver: driver.find_element(By.CSS_SELECTOR, 'span.profile-user_info__walet-text > span.inline'))
    money = float(reduce(lambda sp, repl: sp.replace(*repl), sings_to_remove, money.text))

    # Telegram RU 1шт tdata для Telegram Portable exe - Ручная, Отлежка: 7 дн+, Пол: mix. AccsFarm


    if money >= 1000:
        
        money = int(money - 600)
        print(f'Баланс {money}')
    
        products = WebDriverWait(browser, 3).until(lambda driver: driver.find_elements(By.CSS_SELECTOR, 'div.profileList__card.profileList-card'))

        for product in products:
            card_name = product.find_element(By.CSS_SELECTOR, 'a.profileList-card__name').text
            # card_name_count = int(card_name.split('шт')[0].split('RU')[-1].strip())

            # Telegram Session регистраця 21.08.2022 Пол - Жен.
            # if 'Telegram Session регистраця 21.08.2022 Пол - Жен.' in card_name:

            if 'telegram ru' in card_name.lower():
                
                count = product.find_element(By.CSS_SELECTOR, 'div.profileList-card__counter')
                count = int(reduce(lambda sp, repl: sp.replace(*repl), sings_to_remove, count.text).split(':')[-1].strip())
                
                price = product.find_element(By.CSS_SELECTOR, 'span[class="inline"]')
                price = float(reduce(lambda sp, repl: sp.replace(*repl), sings_to_remove, price.text).split(':')[-1])

                count_to_buy = int(money // price)

                if count_to_buy >= count:
                    count_to_buy = count
                
                buy_btn = product.find_element(By.CSS_SELECTOR, 'div.cardgood__btn > button').click()
                break
        
        card_element_buy = WebDriverWait(browser, 3).until(lambda driver: driver.find_element(By.CSS_SELECTOR, 'div.popup__content.pay-content'))
        
        input_quantity = card_element_buy.find_element(By.CSS_SELECTOR, 'input#quantity')
        input_quantity.click()
        time.sleep(0.2)
        input_quantity.clear()
        input_quantity.send_keys(count_to_buy)

        checkbox = card_element_buy.find_element(By.CSS_SELECTOR, 'input#confirm-rule')
        checkbox.click()

        buy = card_element_buy.find_element(By.CSS_SELECTOR, 'button.confirm')
        buy.click()
        print(buy.text)
        await notify()
    else:
        print('Мало денег, пополни баланс')
    

async def main():
    
    browser = check_product()
    await buy_product(browser)
    


if __name__ == "__main__": 
    asyncio.run(main())
