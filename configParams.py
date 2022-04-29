import json

config = json.loads(open('AUTH/configFile.txt', 'r').read()) # Config File with All Parameters

# Data Collection Params
start_date = config["start_date"]
start_date = int(start_date.split()[0])
timeframe = config["timeframe"]
minutes_from_market_start = config["minutes_from_market_start"]

# Pair Trading Params
spread = config["spread"]
pair = config["pair"]

n_std = config["n_std"]
close_at_x_std_dev = config["close_at_x_std_dev"]

pairs = pair.split('/')
ticker_A = pairs[0]
ticker_B = pairs[1]

# % Capital / Trade
trade_capital_percent = config["% allocation per trade"]

per_trade_capital_percent = trade_capital_percent