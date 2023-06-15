import csv
import datetime
import os


def save_portfolio_to_csv(assets, values):
    folder_name = 'crypto_info'
    os.makedirs(folder_name, exist_ok=True)

    filename = f'{folder_name}/data_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv'
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['Asset', 'Value']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for i, asset in enumerate(assets):
            writer.writerow({'Asset': asset, 'Value': values[i]})

