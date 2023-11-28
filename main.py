import os
import requests
from twilio.rest import Client
from dotenv import load_dotenv
from itertools import islice
from datetime import datetime

STOCK = "RIVN"
COMPANY_NAME = "Rivian"
FUNCTION = "TIME_SERIES_DAILY"
ALPHA_VANTAGE_ENDPOINT = "https://www.alphavantage.co/query"
NEWS_API_ENDPOINT = "https://newsapi.org/v2/everything"

load_dotenv()

API_KEY = os.getenv('API_KEY')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_FROM = os.getenv('TWILIO_FROM')
TWILIO_TO = os.getenv('TWILIO_TO')
ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

account_sid = TWILIO_ACCOUNT_SID
auth_token = TWILIO_AUTH_TOKEN
client = Client(account_sid, auth_token)

def send_message(stock_alert):
    message = client.messages \
        .create(
        body=stock_alert,
        from_=TWILIO_FROM,
        to=TWILIO_TO,

    )
    print(message.status)

def is_notable_change(yesterday_price, day_before_yesterday_price):
    '''sends back stock price change between yesterday and the day before that'''
    is_change = (yesterday_price - day_before_yesterday_price) * 100 / day_before_yesterday_price
    return is_change

## STEP 2: Use https://newsapi.org
# Instead of printing ("Get News"), actually get the first 3 news pieces for the COMPANY_NAME.
def get_news(company_name:str, change: float):
    '''Get news from the News API for the company in question'''
    parameters = {
        "q": company_name,
        "apikey": NEWS_API_KEY,
        "from": datetime.now().strftime("%x"),
        "to":datetime.now().strftime("%x"),
        "searchIn": "title"
    }
    response = requests.get(NEWS_API_ENDPOINT,params=parameters)
    response.raise_for_status()
    news_info = response.json()
    news_info_subset = news_info['articles'][:3]

    ## STEP 3: Use https://www.twilio.com
    # Send a seperate message with the percentage change and each article's title and description to your phone number.
    for article in news_info_subset:
        stock_alert = "\r\n"
        stock_alert = STOCK
        stock_alert +=  "🔻" if change < 0 else "🔺"
        stock_alert += str(round(change))
        stock_alert += "%"
        stock_alert += "\r\nHeadline: \r\n"
        stock_alert += article['title']
        stock_alert += "\r\nBrief: \r\n"
        stock_alert += article['description']
        send_message(stock_alert)

## STEP 1: Use https://www.alphavantage.co
def call_API(function_val:str, symbol:str, apikey: str):
    '''All this function does is call the Alpha Vantage API and retrieves ticker data for the input stock symbol'''
    parameters = {
        "function": function_val,
        "symbol": symbol,
        "apikey": apikey,
    }
    # Call the Alpha Vantage API, retrieve ticker data.
    response = requests.get(ALPHA_VANTAGE_ENDPOINT,params=parameters)
    response.raise_for_status()
    ticker_data = response.json()
    return ticker_data

def get_ticker_info():
    ''' this function calls all the other functions
    - first it calls the Alpha Vantage API
    - then it retrives news for the company
    - finally it sends out three text messages - one for each recent news story about the company'''
    ticker_info = call_API(FUNCTION,STOCK,ALPHA_VANTAGE_KEY)

    # get yesterday's and the day before's stock prices
    # we know the most recent prices will be the first two items in the array so get a slice of it,
    # this is a dictionary and we are only interested in its values, then convert it to a list so we don't get a dict_values object
    recent_stock_prices = list(dict(islice(ticker_info['Time Series (Daily)'].items(), 2)).values())

    if len(recent_stock_prices) == 2:
        yesterday_price = float(recent_stock_prices[0]["4. close"])
        day_before_yesterday_price = float(recent_stock_prices[1]["4. close"])

    change = is_notable_change(yesterday_price, day_before_yesterday_price)

    get_news(COMPANY_NAME,change)




get_ticker_info()

#Optional: Format the SMS message like this:
"""
TSLA: 🔺2%
Headline: Were Hedge Funds Right About Piling Into Tesla Inc. (TSLA)?. 
Brief: We at Insider Monkey have gone over 821 13F filings that hedge funds and prominent investors are required to file by the SEC The 13F filings show the funds' and investors' portfolio positions as of March 31st, near the height of the coronavirus market crash.
or
"TSLA: 🔻5%
Headline: Were Hedge Funds Right About Piling Into Tesla Inc. (TSLA)?. 
Brief: We at Insider Monkey have gone over 821 13F filings that hedge funds and prominent investors are required to file by the SEC The 13F filings show the funds' and investors' portfolio positions as of March 31st, near the height of the coronavirus market crash.
"""

