import requests, asyncio
from bs4 import BeautifulSoup
import sys, json, re, time
from telethon import TelegramClient



class Watcher:

    def __init__(self, store_name: str, product_id: int | str | None = None, timeout: float = 1.5):
        self.store_name = store_name
        self.product_id = product_id
        self.session = requests.Session()
        self.timeout = timeout
        self.cookies = self.get_cookies()
        self.headers = {
            'authority': 'hstock.org',
            'accept': '*/*',
            'x-requested-with': 'XMLHttpRequest',
            'user-agent': self.get_latest_useragent(),
            'x-xsrf-token': self.cookies['XSRF-TOKEN']
        }

    def __del__(self):
        self.session.close()

    @staticmethod
    def get_cookies():
        with open('hstock_session.json', 'r', encoding='utf-8') as file:
            return {k['name']: k['value'] for k in json.load(file)}

    @staticmethod
    def html(html: str | bytes, _parser: str = "lxml") -> BeautifulSoup:
        return BeautifulSoup(html, _parser)

    def get_latest_useragent(self) -> str | None:
        """
        Returns:
            str | None: Trying to get the latest useragent for your browser
            
        It's can be useful if site has cloudflare and checks your platform with useragent
        and compare it. But it may be not enough, check on cookies as well.
        Also it's just a way to get it faster. Better use selenium/any instead
        """
        
        linux_ua = 'Mozilla/5.0 (X11; Linux x86_64)'
        windows_ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    
        response = self.session.get('https://www.whatismybrowser.com/guides/the-latest-user-agent/windows')
        data = self.html(response.content).select('table > tbody > tr')
        new_ua = None
        for col in data:
            chrome = col.select_one('td > b')
            if chrome and chrome.get_text(strip=True).lower() == 'chrome':
                ua = col.select_one('span.code')
                if ua:
                    new_ua = ua.get_text(strip=True)
                    break
        if new_ua:
            new_data = new_ua.split(')', 1)[-1]
            
            platform = sys.platform
            if platform == 'win32':
                new_ua = f'{windows_ua}{new_data}'
            elif platform == 'linux' or platform == 'linux2':
                new_ua = f'{linux_ua}{new_data}'
            else:
                raise Exception(f'This function expected Linux or Windows platform, not {platform}')

        return new_ua


    def get_csrf_token(self):
        response = self.session.get(f"https://hstock.org/store/{self.store_name}", headers=self.headers, cookies=self.cookies)
        csrf = self.html(response.content).select_one('meta[name="csrf-token"]')
        if csrf:
            csrf = csrf.get('content')
        else:
            raise Exception('No csrf token, check cookies')
        self.headers.update({
            'x-csrf-token': csrf
        })


    def watch_and_buy(self, count_to_buy: int = None):
        while True:
            try:
                response = self.session.get(f"https://hstock.org/store/{self.store_name}", headers=self.headers, cookies=self.cookies)
            except Exception as ex:
                print(f'Unexpected error: {ex.__class__.__name__}\n{ex}')
                time.sleep(2)
                continue

            raw_html = response.content
            html = self.html(raw_html)
            products = html.select('div.profileList__card.profileList-card')
            is_indonesian = False
            if products:
                balance = self.get_balance(raw_html)
              
                if self.product_id is not None and str(self.product_id).isnumeric():
                    count = self.get_product_count(raw_html)
                    price = self.get_product_price(raw_html)
                    return self.buy(balance=balance, count=count, price=price)

                for product in products:
                    product_id = product.select_one('div.profileList-card__img')
                    product_name = product.select_one('a.profileList-card__name')
                    if product_name and product_id:
                        product_id = product_id.get('style').split('/')[-2]
                        product_name = product_name.get_text(strip=True)
                        if 'telegram ru' in product_name.lower():
                        # if 'telegram england' in product_name.lower():
                            self.product_id = product_id
                            count = self.get_product_count(raw_html)
                            price = self.get_product_price(raw_html)
                            return self.buy(balance=balance, count=count, price=price, count_to_buy=count_to_buy)

                        if 'indonesia' in product_name.lower():
                            is_indonesian = True
                if is_indonesian:
                    print('Only indonesians accounts available!')
            else:
                print('No products in store')
            
            time.sleep(self.timeout)


    def get_balance(self, store_content):
        
        money = self.html(store_content).select_one('div.profile-user_info__walet > balance')
        if money:
            money = money.get('balanceprop')
        else:
            raise Exception('No profile info')
        return float(money)


    def get_product_count(self, store_content):
        products = self.html(store_content).select('div.profileList__card.profileList-card')
    
        for product in products:
            product_id = product.select_one('div.profileList-card__img')
            if product_id:
                product_id = product_id.get('style').split('/')[-2] 
                if product_id == str(self.product_id):
                    count = product.select_one('div.profileList-card__counter')
                    if count:
                        count = count.get_text(strip=True)
                        return int(re.search(r'\d+', count).group())
    

    def get_product_price(self, store_content):
        products = self.html(store_content).select('div.profileList__card.profileList-card')

        for product in products:
            product_id = product.select_one('div.profileList-card__img')
            if product_id:
                product_id = product_id.get('style').split('/')[-2] 
                if product_id == str(self.product_id):
                    product_price = product.select_one('a.profileList-card__price')
                    if product_price:
                        product_price = product_price.select_one('format-price').get(':price')
                        return float(re.search(r'[\d+\,\.]+', product_price).group().replace(',', '.'))


    # https://hstock.org/cart/gettotalsumm/11700/0 # check price by post request
    def buy(self, balance: float, count: int, price: float, count_to_buy: int = None):
        self.get_csrf_token()
        if not all([balance is not None, count is not None, price is not None]):
            raise Exception('Couldnt fetch data')

        money = int(balance)
        max_buy = int(money // price)
        

        if count_to_buy and balance >= 400:
            if count_to_buy <= count and count_to_buy <= max_buy:
                to_buy = count_to_buy
        elif balance >= 400:
            if max_buy > count:
                to_buy = count
        else:
            print('Ты бомж!')
   
        response = self.session.post(f'https://hstock.org/cart/buy/{self.product_id}/{to_buy}', headers=self.headers, cookies=self.cookies)
        resp_json = response.json()

        if response.status_code == 200 and resp_json.get('status') == 'success':
            print('Покупка была успешной')
        else:
            print('Покупка не удалась', resp_json)
        

async def notify():
    client = TelegramClient('+447761613808', 1, '1')
    try:
        await client.connect()
        # await client.send_message('aenisx', f'Accounts on AccsFarm available!!!')
        # await client.send_message('hpphme', f'Accounts on AccsFarm available!!!')
        await client.send_message('dimaprog22', f'Accounts on AccsFarm available!!!')
    except BaseException as e: 
        print(e)
    finally: 
        await client.disconnect()
    

async def main():
    try:
        htock = Watcher(store_name='tgacc-5322f8bb', product_id=None)
        htock.watch_and_buy()
        await notify()
        
    except KeyboardInterrupt:
        print('Canceled')



if __name__ == '__main__':
    asyncio.run(main())
    





