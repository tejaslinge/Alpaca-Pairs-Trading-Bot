# Alpaca-Pairs-Trading-Bot

Pairs Trading Bot built using Alpaca API. Read along to understand the buy/sell criteria:

1. Calculate ***mean*** and ***standard deviation*** of the ***spread*** of stocks A and B.
2. If ***mean - n*std > spread (last candle formed)***, ***buy A***, ***sell B***, else (if mean - n*std < spread) vice-versa.
3. The bot closes both positions once the spread reaches mean again
4. Repeat steps 1-4

# Functions Used

1. Collects data for both tickers, calculates spread and returns a df with 4 columns: ***timestamp***, ***A*** (price of A at close of the candle), ***B***, and ***Spread***
```
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
```


2. Calculates required position size for the stock to buy
```
def calculate_targetPositionSize(stock_to_buy: str):
    # Returns number of stocks to buy and short
    cashToUse = float(api.get_account().cash) * per_trade_capital_percent * 0.01
    buy_amount = cashToUse
    price_ticker = api.get_latest_trade(stock_to_buy).p
    targetPositionSize = ((float(buy_amount)) / (price_ticker)) # Calculates required position size
    targetPositionSize = math.floor(targetPositionSize)
    return targetPositionSize
```


3. Places long and short orders and returns 2 strings that will be used to alert the user the moment trades are placed
```
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
```


4. Sends mail alerts
```
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
```


5. Sometimes the user may want to wait for some time before they trading because of high bid/ask spread at the start of the market. The following function would help with it. It calculates the time to wait before starting to trade and sleeps till then.
```
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
```
