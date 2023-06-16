from flask import Flask, render_template, request
from binance.client import Client
from binance.enums import KLINE_INTERVAL_1DAY, KLINE_INTERVAL_4HOUR, KLINE_INTERVAL_1HOUR
import configparser
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import csv
import os
import time

app = Flask(__name__, template_folder='templates')

config = configparser.ConfigParser()
config.read_file(open('secret.cfg'))

actual_api_key = config.get('BINANCE', 'ACTUAL_API_KEY')
actual_secret_key = config.get('BINANCE', 'ACTUAL_SECRET_KEY')

client = Client(actual_api_key, actual_secret_key)
client.API_URL = 'https://api.binance.com/api'

symbol_interval_mapping = {
    'BTCUSDT': KLINE_INTERVAL_1DAY,
    'BNBUSDT': KLINE_INTERVAL_4HOUR,
    'ETHUSDT': KLINE_INTERVAL_1HOUR
}

csv_file = os.path.join(os.path.dirname(__file__), 'crypto_info', 'data.csv')


def save_to_csv(candlestick_data):
    with open(csv_file, 'a', newline='') as file:
        writer = csv.writer(file)

        is_empty = file.tell() == 0

        if is_empty:
            writer.writerow(['Timestamp', 'Open', 'High', 'Low', 'Close'])

        for i in range(len(candlestick_data['timestamps'])):
            row = [
                candlestick_data['timestamps'][i],
                candlestick_data['open'][i],
                candlestick_data['high'][i],
                candlestick_data['low'][i],
                candlestick_data['close'][i]
            ]
            writer.writerow(row)


def update_last_update_time(symbol, current_time):
    with open(csv_file, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([symbol, current_time])


def get_last_update_time():
    try:
        with open(csv_file, 'r') as file:
            reader = csv.reader(file)
            last_row = list(reader)[-1]
            return float(last_row[1])
    except (FileNotFoundError, IndexError):
        return 0.0


def get_candlestick_data(symbol, interval):
    if interval == '1d':
        interval = KLINE_INTERVAL_1DAY
    elif interval == '4h':
        interval = KLINE_INTERVAL_4HOUR
    elif interval == '1h':
        interval = KLINE_INTERVAL_1HOUR
    else:
        raise ValueError(f"Invalid interval: {interval}")

    candles = client.get_klines(
        symbol=symbol,
        interval=interval,
        limit=30
    )

    timestamps = []
    open_prices = []
    high_prices = []
    low_prices = []
    close_prices = []

    for candle in candles:
        timestamps.append(candle[0])
        open_prices.append(float(candle[1]))
        high_prices.append(float(candle[2]))
        low_prices.append(float(candle[3]))
        close_prices.append(float(candle[4]))

    return {
        'timestamps': timestamps,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices
    }


def create_candlestick_chart(symbol, data):
    fig = make_subplots(rows=1, cols=1)

    fig.add_trace(go.Candlestick(
        x=data['timestamps'],
        open=data['open'],
        high=data['high'],
        low=data['low'],
        close=data['close']
    ))

    fig.update_layout(
        title=f'Candlestick Chart - {symbol}',
        xaxis=dict(
            rangeslider=dict(
                visible=False
            )
        ),
        yaxis=dict(
            fixedrange=True
        )
    )

    return fig


def save_to_csv_if_needed(symbol, interval, save_interval=3600):
    last_update_time = get_last_update_time()

    current_time = time.time()
    if current_time - last_update_time >= save_interval:
        candlestick_data = get_candlestick_data(symbol, interval)
        save_to_csv(candlestick_data)
        update_last_update_time(symbol, current_time)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        symbol = request.form['symbol']
        interval = request.form['interval']
        if 'save_interval' in request.form:
            save_interval = int(request.form['save_interval'])
        else:
            save_interval = 3600
    else:
        symbol = 'BTCUSDT'
        interval = KLINE_INTERVAL_1DAY
        save_interval = 3600

    candlestick_data = get_candlestick_data(symbol, symbol_interval_mapping[symbol])
    chart = create_candlestick_chart(symbol, candlestick_data)

    save_to_csv_if_needed(symbol, interval, save_interval)

    chart_html = chart.to_html(full_html=False)

    return render_template('index.html', chart=chart_html, symbol=symbol, interval=interval, candlestick_data=candlestick_data)


if __name__ == '__main__':
    app.run()