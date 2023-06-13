from flask import Flask, render_template, jsonify
from binance.client import Client
import configparser
from binance.websockets import BinanceSocketManager
import time

app = Flask(__name__, template_folder='templates')

config = configparser.ConfigParser()
config.read_file(open('secret.cfg'))
test_api_key = config.get('BINANCE', 'TEST_API_KEY')
test_secret_key = config.get('BINANCE', 'TEST_SECRET_KEY')

client = Client(test_api_key, test_secret_key)
client.API_URL = 'https://testnet.binance.vision/api'

info = client.get_account()

assets = []
values = []
for index in range(len(info['balances'])):
    for key in info['balances'][index]:
        if key == 'asset':
            assets.append(info['balances'][index][key])
        if key == 'free':
            values.append(info['balances'][index][key])

token_usdt = {}
token_pairs = []

for token in assets:
    if token != 'USDT':
        token_pairs.append(token + 'USDT')


def streaming_data_process(msg):
    """
    Function to process the received messages and add the latest token pair price
    into the token_usdt dictionary
    :param msg: input message
    """
    global token_usdt
    token_usdt[msg['s']] = msg['c']


def total_amount_usdt(assets, values, token_usdt):
    """
    Function to calculate the total portfolio value in USDT
    :param assets: Assets list
    :param values: Assets quantity
    :param token_usdt: Token pair price dict
    :return: total value in USDT
    """
    total_amount = 0
    for i, token in enumerate(assets):
        if token != 'USDT':
            total_amount += float(values[i]) * float(token_usdt[token + 'USDT'])
        else:
            total_amount += float(values[i]) * 1
    return total_amount


def total_amount_btc(assets, values, token_usdt):
    """
    Function to calculate the total portfolio value in BTC
    :param assets: Assets list
    :param values: Assets quantity
    :param token_usdt: Token pair price dict
    :return: total value in BTC
    """
    total_amount = 0
    for i, token in enumerate(assets):
        if token != 'BTC' and token != 'USDT':
            total_amount += float(values[i]) * float(token_usdt[token + 'USDT']) / float(token_usdt['BTCUSDT'])
        if token == 'BTC':
            total_amount += float(values[i]) * 1
        else:
            total_amount += float(values[i]) / float(token_usdt['BTCUSDT'])
    return total_amount


def assets_usdt(assets, values, token_usdt):
    """
    Function to convert all assets into the equivalent USDT value
    :param assets: Assets list
    :param values: Assets quantity
    :param token_usdt: Token pair price dict
    :return: list of asset values in USDT
    """
    assets_in_usdt = []
    for i, token in enumerate(assets):
        if token != 'USDT':
            assets_in_usdt.append(float(values[i]) * float(token_usdt[token + 'USDT']))
        else:
            assets_in_usdt.append(float(values[i]) * 1)
    return assets_in_usdt


bm = BinanceSocketManager(client)
for tokenpair in token_pairs:
    conn_key = bm.start_symbol_ticker_socket(tokenpair, streaming_data_process)
bm.start()
time.sleep(5)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/data')
def get_data():
    data = {
        'total_amount_usdt': total_amount_usdt(assets, values, token_usdt),
        'total_amount_btc': total_amount_btc(assets, values, token_usdt),
        'token_usdt_bnb': float(token_usdt['BNBUSDT']),
        'assets': assets,
        'assets_usdt': assets_usdt(assets, values, token_usdt),
        'values': values
    }
    return jsonify(data)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8050, debug=False)
