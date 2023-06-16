from flask import Flask, render_template, request
from binance.client import Client
import configparser
from binance.enums import KLINE_INTERVAL_1DAY, KLINE_INTERVAL_4HOUR, KLINE_INTERVAL_1HOUR
from plotly.subplots import make_subplots
import plotly.graph_objects as go

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


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        symbol = request.form['symbol']
        interval = request.form['interval']
    else:
        symbol = 'BTCUSDT'
        interval = KLINE_INTERVAL_1DAY

    candlestick_data = get_candlestick_data(symbol, symbol_interval_mapping[symbol])
    chart = create_candlestick_chart(symbol, candlestick_data)

    # Convert the chart to HTML code for embedding in the template
    chart_html = chart.to_html(full_html=False)

    return render_template('index.html', chart=chart_html, symbol=symbol, interval=interval, candlestick_data=candlestick_data)


if __name__ == '__main__':
    app.run()