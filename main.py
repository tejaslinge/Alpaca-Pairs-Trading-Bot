import pandas as pd
import json
from datetime import datetime as dt
from datetime import timedelta
import time
import pytz
import math

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import alpaca_trade_api as alpaca
from configParams import *

# Files
key = json.loads(open('AUTH/authAlpaca.txt', 'r').read())
api = alpaca.REST(key['APCA-API-KEY-ID'], key['APCA-API-SECRET-KEY'], base_url= key['BASE-URL'], api_version = 'v2')

# Function to fetch data
# Change get_data to fetch data from Alpaca
def get_data(ticker_A, ticker_B, timeframe = timeframe, start_date = int(start_date)):
    
    print('Collecting ticker A')
    df_A = api.get_bars(ticker_A, timeframe, (dt.now() - timedelta(days = start_date)).strftime("%Y-%m-%d")).df
    df_A.reset_index(inplace = True)
    df_A = df_A[['timestamp', 'close']]
    df_A.columns = ['Timestamp', "A"]
    df_A['Timestamp'] = pd.to_datetime(df_A['Timestamp']).dt.strftime('%Y-%m-%d %H:%M')
    
    print('Collecting ticker B')
    df_B = api.get_bars(ticker_B, timeframe, (dt.now() - timedelta(days = start_date)).strftime("%Y-%m-%d")).df
    df_B.reset_index(inplace = True)
    df_B = df_B[['timestamp', 'close']]
    df_B.columns = ['Timestamp', "B"]
    df_B['Timestamp'] = pd.to_datetime(df_B['Timestamp']).dt.strftime('%Y-%m-%d %H:%M')

    df = pd.merge(df_A, df_B, how = 'inner', on = 'Timestamp')
    df['Spread'] = df['A'] - df['B']

    return df

def calculate_targetPositionSize(stock_to_buy: str):
    # Returns number of stocks to buy and short
    cashToUse = float(api.get_account().cash) * per_trade_capital_percent * 0.01
    buy_amount = cashToUse
    price_ticker = api.get_latest_trade(stock_to_buy).p
    targetPositionSize = ((float(buy_amount)) / (price_ticker)) # Calculates required position size
    targetPositionSize = math.floor(targetPositionSize)
    return targetPositionSize

def open_trades(stock_to_buy, stock_to_short, targetPositionSize):

    buy_price = api.get_latest_trade(stock_to_buy).p
    sell_price = api.get_latest_trade(stock_to_short).p

    # num_stocks = short_amount / stock_price
    api.submit_order(stock_to_short, targetPositionSize, 'sell')
    mail_content_short = '''TRADE ALERT: SELL Order Placed for {} Stock(s) of {} at ${}'''.format(targetPositionSize, stock_to_short, sell_price)

    api.submit_order(str(stock_to_buy), targetPositionSize, "buy") # Market order to open position
    mail_content_long = '''TRADE ALERT: BUY Order Placed for {} Stock(s) of {} at ${}'''.format(targetPositionSize, stock_to_buy, buy_price)
    print(mail_content_long)
    print(mail_content_short)
    return mail_content_long, mail_content_short


def mail_alert(mail_content, sleep_time):
    # The mail addresses and password
    sender_address = 'SENDER_EMAIL'
    sender_pass = 'SENDER_EMAIL_PASSWORD'
    receiver_address = 'RECEIVER_EMAIL'

    # Setup MIME
    message = MIMEMultipart()
    message['From'] = 'Trading Bot'
    message['To'] = receiver_address
    message['Subject'] = 'Technical Trading Bot'
    
    # The body and the attachments for the mail
    message.attach(MIMEText(mail_content, 'plain'))

    # Create SMTP session for sending the mail
    session = smtplib.SMTP('smtp.gmail.com', 587)  # use gmail with port
    session.starttls()  # enable security

    # login with mail_id and password
    session.login(sender_address, sender_pass)
    text = message.as_string()
    session.sendmail(sender_address, receiver_address, text)
    session.quit()
    time.sleep(sleep_time)


def check_clock():
    
    if api.get_clock().is_open == False:
        return False
    
    wait_time = minutes_from_market_start * 60 

    market_start_time = dt.now().strftime('%Y-%m-%d') + ' 9:30:00'
    current_time = dt.now().astimezone(pytz.timezone('America/New_York')).strftime('%Y-%m-%d %H:%M:%S')
    time_since_start = (dt.strptime(current_time,"%Y-%m-%d %H:%M:%S") - dt.strptime(market_start_time,"%Y-%m-%d %H:%M:%S")).seconds

    trade_start = time_since_start >= wait_time

    if trade_start:
        mail_content = 'The Bot started on {} at {}'.format(dt.now().strftime('%Y-%m-%d'), dt.now().strftime('%H:%M:%S'))
        print(mail_content)
        mail_alert(mail_content, 0)
        return True
    else:
        print("Sleeping for {}".format(wait_time - time_since_start))
        time.sleep(wait_time - time_since_start)
        return check_clock()

def main():

    clock = check_clock()

    if not clock:
        mail_content = 'The market is closed now. The Bot stopped on {} at {}'.format(dt.now().strftime('%Y-%m-%d'), dt.now().strftime('%H:%M:%S'))
        mail_alert(mail_content, 0)
        return 0

    while True:
        try:
            if api.get_account().pattern_day_trader == True:
                mail_alert('Pattern day trading notification: The Bot stopped on {} at {}'.format(dt.now().strftime('%Y-%m-%d'), dt.now().strftime('%H:%M:%S')), 0)
                break
            
            if len(api.list_positions()) == 0:
                print('No Open Positions, Checking Criteria')
                df = get_data(ticker_A, ticker_B)
                mean = df['Spread'].mean()
                std = df['Spread'].std()

                if df['Spread'].loc[df.shape[0] - 1] < mean - (n_std * std):
                    print('Spread < (Mean - {} * Std)'.format(n_std))
                    targetPositionSize = calculate_targetPositionSize(ticker_A)
                    mail_content_long, mail_content_short = open_trades(ticker_A, ticker_B, targetPositionSize)
                    # mail_content_short = sell(ticker_B, targetPositionSize)
                    mail_alert(mail_content_long, 0)
                    mail_alert(mail_content_short, 20)
                
                elif df['Spread'].loc[df.shape[0] - 1] > mean + (n_std * std):
                    print('Spread > (Mean - {} * Std)'.format(n_std))
                    # mail_content_long, targetPositionSize = buy(ticker_B)
                    targetPositionSize = calculate_targetPositionSize(ticker_B)

                    # mail_content_short = sell(ticker_A, targetPositionSize)
                    mail_content_long, mail_content_short = open_trades(ticker_B, ticker_A, targetPositionSize)
                    mail_alert(mail_content_short, 0)
                    mail_alert(mail_content_long, 20)

                else:
                    time.sleep(10)
                
            else:
                print('Open Positions')
                df = get_data(ticker_A, ticker_B)
                mean = df['Spread'].mean()
                std = df['Spread'].std()

                if int(api.get_position(ticker_A).qty) > 0:
                    if df['Spread'].loc[df.shape[0] - 1] >= mean + (close_at_x_std_dev * std):
                        print('Spread >= Mean, Closing Positions Now')
                        api.close_all_positions()
                    else:
                        time.sleep(10)

                elif int(api.get_position(ticker_A).qty) < 0:
                    if df['Spread'].loc[df.shape[0] - 1] <= mean + (close_at_x_std_dev * std):
                        print('Spread <= Mean, Closing Positions Now')
                        api.close_all_positions()
                    else:
                        time.sleep(10)
        
        except Exception as e:
            stop_mail = 'The Bot stopped on {} at {}'.format(dt.now().strftime('%Y-%m-%d'), dt.now().strftime('%H:%M:%S'))
            mail_alert('EXCEPTION: {}'.format(e), 0)
            mail_alert(stop_mail, 0)
            print(e)
            break

if __name__ == "__main__":
    main()