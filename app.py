from flask import Flask, render_template, request
from binance.client import Client
from binance.enums import (
    KLINE_INTERVAL_1DAY,
    KLINE_INTERVAL_4HOUR,
    KLINE_INTERVAL_1HOUR
)
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from dotenv import load_dotenv
import threading
import csv
import os
import time
import psycopg2
import sched


class App:
    def __init__(self):
        self.app = Flask(__name__, template_folder='templates')
        self.client = self._create_binance_client()
        self.conn = self._create_postgresql_connection()
        self.cur = self.conn.cursor()
        self.csv_file = os.path.join(os.path.dirname(__file__), 'crypto_info', 'data.csv')
        self.symbol_interval_mapping = {
            'BTCUSDT': KLINE_INTERVAL_1DAY,
            'BNBUSDT': KLINE_INTERVAL_4HOUR,
            'ETHUSDT': KLINE_INTERVAL_1HOUR
        }
        self.csv_thread = None
        self.db_thread = None

    def _create_binance_client(self):
        actual_api_key = os.getenv('ACTUAL_API_KEY')
        actual_secret_key = os.getenv('ACTUAL_SECRET_KEY')

        client = Client(actual_api_key, actual_secret_key)
        client.API_URL = 'https://api.binance.com/api'

        return client

    def _create_postgresql_connection(self):
        load_dotenv()
        conn = psycopg2.connect(
            host="localhost",
            database="postgres",
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD")
        )

        cur = conn.cursor()

        cur.execute('CREATE TABLE IF NOT EXISTS candlestick_data ('
                    'id serial PRIMARY KEY,'
                    'symbol varchar(10) NOT NULL,'
                    'interval varchar(10) NOT NULL,'
                    'timestamp bigint NOT NULL,'
                    'open numeric NOT NULL,'
                    'high numeric NOT NULL,'
                    'low numeric NOT NULL,'
                    'close numeric NOT NULL'
                    ');')

        return conn

    def save_to_csv(self, symbol, interval, candlestick_data):
        with open(self.csv_file, 'a', newline='') as file:
            writer = csv.writer(file)

            is_empty = file.tell() == 0

            if is_empty:
                writer.writerow(['Timestamp', 'Open', 'High', 'Low', 'Close'])

            writer.writerow(['Symbol: ' + symbol, 'Interval: ' + interval])

            for i in range(len(candlestick_data['timestamps'])):
                row = [
                    candlestick_data['timestamps'][i],
                    candlestick_data['open'][i],
                    candlestick_data['high'][i],
                    candlestick_data['low'][i],
                    candlestick_data['close'][i]
                ]
                writer.writerow(row)

    def save_to_database(self, symbol, interval, candlestick_data):
        data = []
        for i in range(len(candlestick_data['timestamps'])):
            timestamp = candlestick_data['timestamps'][i]
            open_price = candlestick_data['open'][i]
            high_price = candlestick_data['high'][i]
            low_price = candlestick_data['low'][i]
            close_price = candlestick_data['close'][i]

            data.append((symbol, interval, timestamp, open_price, high_price, low_price, close_price))

        try:
            self.cur.executemany('INSERT INTO candlestick_data (symbol, interval, timestamp, open, high, low, close) '
                                 'VALUES (%s, %s, %s, %s, %s, %s, %s)', data)
            self.conn.commit()
        except psycopg2.Error as e:
            print("Error saving data to database:", e)

    def update_last_update_time(self, symbol, current_time):
        with open(self.csv_file, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([symbol, current_time])

    def get_last_update_time(self):
        try:
            with open(self.csv_file, 'r') as file:
                reader = csv.reader(file)
                last_row = list(reader)[-1]
                return float(last_row[1])
        except (FileNotFoundError, IndexError):
            return 0.0

    def get_candlestick_data(self, symbol, interval):
        if interval == '1d':
            interval = KLINE_INTERVAL_1DAY
        elif interval == '4h':
            interval = KLINE_INTERVAL_4HOUR
        elif interval == '1h':
            interval = KLINE_INTERVAL_1HOUR
        else:
            raise ValueError(f"Invalid interval: {interval}")

        candles = self.client.get_klines(
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

    def create_candlestick_chart(self, symbol, interval, data):
        fig = make_subplots(rows=1, cols=1)

        fig.add_trace(go.Candlestick(
            x=data['timestamps'],
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close']
        ))

        if interval == KLINE_INTERVAL_1DAY:
            xaxis_title = 'Date'
            xaxis_tickformat = '%Y-%m-%d'
        elif interval == KLINE_INTERVAL_4HOUR:
            xaxis_title = 'Time'
            xaxis_tickformat = '%H:%M'
        elif interval == KLINE_INTERVAL_1HOUR:
            xaxis_title = 'Time'
            xaxis_tickformat = '%H:%M'
        else:
            xaxis_title = 'Time'
            xaxis_tickformat = ''

        fig.update_layout(
            title=f'Candlestick Chart - {symbol}',
            xaxis=dict(
                title=xaxis_title,
                rangeslider=dict(
                    visible=False
                ),
                tickformat=xaxis_tickformat
            ),
            yaxis=dict(
                fixedrange=True
            )
        )

        return fig

    def save_data_periodically(self, symbol, interval, save_interval, scheduler):
        candlestick_data = self.get_candlestick_data(symbol, interval)
        self.save_to_csv(symbol, interval, candlestick_data)
        self.save_to_database(symbol, interval, candlestick_data)
        self.update_last_update_time(symbol, time.time())

        scheduler.enter(save_interval, 1, self.save_data_periodically, argument=(symbol, interval, save_interval, scheduler))

    def save_to_csv_and_db(self, symbol, interval, save_interval=3600):
        scheduler = sched.scheduler(time.time, time.sleep)
        scheduler.enter(save_interval, 1, self.save_data_periodically, argument=(symbol, interval, save_interval, scheduler))
        threading.Thread(target=scheduler.run).start()



    def run(self):
        @self.app.route('/', methods=['GET', 'POST'])
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

            candlestick_data = self.get_candlestick_data(symbol, self.symbol_interval_mapping[symbol])
            chart = self.create_candlestick_chart(symbol, interval, candlestick_data)

            self.save_to_csv_and_db(symbol, interval, save_interval)

            if self.csv_thread is not None:
                self.csv_thread.join()
            if self.db_thread is not None:
                self.db_thread.join()

            chart_html = chart.to_html(full_html=False)

            return render_template('index.html', chart=chart_html, symbol=symbol, interval=interval,
                                   candlestick_data=candlestick_data)

        self.app.run()


if __name__ == '__main__':
    app = App()
    app.run()