import csv
import os
from models import Portfolio
from app import db


def save_portfolio_to_csv(assets, values):
    folder_name = 'crypto_info'
    os.makedirs(folder_name, exist_ok=True)

    filename = f'{folder_name}/data.csv'
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['Asset', 'Value']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for i, asset in enumerate(assets):
            writer.writerow({'Asset': asset, 'Value': values[i]})


def save_portfolio_to_db(assets, values):
    for i, asset in enumerate(assets):
        portfolio = Portfolio(asset=asset, value=values[i])
        db.session.add(portfolio)

    db.session.commit()
