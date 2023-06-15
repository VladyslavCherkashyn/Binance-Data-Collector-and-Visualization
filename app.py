from flask import Flask, render_template, jsonify
from binance.client import Client
import configparser
from binance.websockets import BinanceSocketManager
from collect_data_csv import save_portfolio_to_csv
import time

app = Flask(__name__, template_folder='templates')


config = configparser.ConfigParser()
config.read_file(open('secret.cfg'))
test_api_key = config.get('BINANCE', 'TEST_API_KEY')
test_secret_key = config.get('BINANCE', 'TEST_SECRET_KEY')

client = Client(test_api_key, test_secret_key)
client.API_URL = 'https://testnet.binance.vision/api'


class CryptoPortfolio:
    def __init__(self):
        self.assets = []
        self.values = []
        self.token_usdt = {}
        self.token_pairs = []
        self.bm = None

    def populate_portfolio(self):
        info = client.get_account()
        for index in range(len(info['balances'])):
            for key in info['balances'][index]:
                if key == 'asset':
                    self.assets.append(info['balances'][index][key])
                if key == 'free':
                    self.values.append(info['balances'][index][key])

        for token in self.assets:
            if token != 'USDT':
                self.token_pairs.append(token + 'USDT')

    def start_streaming_data(self):
        self.bm = BinanceSocketManager(client)
        for tokenpair in self.token_pairs:
            self.bm.start_symbol_ticker_socket(tokenpair, self.streaming_data_process)
        self.bm.start()
        time.sleep(5)

    def streaming_data_process(self, msg):
        self.token_usdt[msg['s']] = msg['c']

    def total_amount_usdt(self):
        total_amount = 0
        for i, token in enumerate(self.assets):
            if token != 'USDT':
                total_amount += float(self.values[i]) * float(self.token_usdt[token + 'USDT'])
            else:
                total_amount += float(self.values[i]) * 1
        return total_amount

    def total_amount_btc(self):
        total_amount = 0
        for i, token in enumerate(self.assets):
            if token != 'BTC' and token != 'USDT':
                total_amount += float(self.values[i]) * float(self.token_usdt[token + 'USDT']) / float(
                    self.token_usdt['BTCUSDT'])
            if token == 'BTC':
                total_amount += float(self.values[i]) * 1
            else:
                total_amount += float(self.values[i]) / float(self.token_usdt['BTCUSDT'])
        return total_amount

    def assets_usdt(self):
        assets_in_usdt = []
        for i, token in enumerate(self.assets):
            if token != 'USDT':
                assets_in_usdt.append(float(self.values[i]) * float(self.token_usdt[token + 'USDT']))
            else:
                assets_in_usdt.append(float(self.values[i]) * 1)
        return assets_in_usdt

    def get_data(self):
        data = {
            'total_amount_usdt': self.total_amount_usdt(),
            'total_amount_btc': self.total_amount_btc(),
            'token_usdt_bnb': float(self.token_usdt['BNBUSDT']),
            'assets': self.assets,
            'assets_usdt': self.assets_usdt(),
            'values': self.values
        }
        save_portfolio_to_csv(self.assets, self.values)
        return data


portfolio = CryptoPortfolio()
portfolio.populate_portfolio()
portfolio.start_streaming_data()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/data')
def get_data():
    data = portfolio.get_data()
    return jsonify(data)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8050, debug=False)
