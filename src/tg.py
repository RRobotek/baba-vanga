import asyncio
import logging
import colorlog

from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.filters import CommandObject
from aiogram.types import FSInputFile, URLInputFile, BufferedInputFile


import io
from decouple import config


from model import predict
from candles import get_candles, get_uniswap_pair_id, get_pair_universe
from render import render
from bc_tools import erc20, common

import pandas as pd
from decimal import Decimal
from print_color import print

w3 = common.connect_web3()

import json


# Set up the logger
def setup_logger():
    logger = logging.getLogger('my_logger')
    logger.setLevel(logging.DEBUG)

    # Create a colored formatter
    formatter = colorlog.ColoredFormatter(
        "%(asctime)s (%(filename)s:%(funcName)s) (%(log_color)s%(levelname)s%(reset)s): %(message)s",
        datefmt='%H:%M:%S',
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
    )
    # Create a console handler and set the formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add the console handler to the logger
    logger.addHandler(console_handler)

    return logger

# Initialize the logger
logger = setup_logger()

def analyse_ca(ca):
    token = erc20.ERC20(w3, ca)
    now = datetime.now()

    # get candles
    pair_universe = get_pair_universe()
    pair_id = get_uniswap_pair_id(pair_universe, str(token.pair_address).lower())
    df = get_candles(pair_id, "15m")
    
    # predict
    predicted_data = predict(df, 30, "15min", "ts_utc", "c")

    # render
    img = render(df, predicted_data, "72 hours")

    # define time periods for trend analysis
    times = [1, 12, 24, 168]  # hours for 1h, 12h, 24h and 1 week (168h)
    trends = {}

    # token supply without decimals
    total_supply = token.get_total_supply('Ether')

    for time in times:
        try:
            logger.info(f'Calcing {time}h trend...', time)
            past_time = now - timedelta(hours=time)
            last_time_period = df[df['ts_utc'] > past_time]

            initial_price = last_time_period.iloc[0]['p']
            final_price = last_time_period.iloc[-1]['p']
            percentage_change = ((final_price - initial_price) / initial_price) * 100

            trends[f'{time}h_trend'] = percentage_change
        except Exception as e:
            logger.error(f"Exception: {e}")


    # get 24h stats
    last_24_hours = df[df['ts_utc'] > (now - timedelta(hours=24))]

    volume_24h = last_24_hours['v'].sum()
    buy_volume_24h = last_24_hours['bv'].sum()
    sell_volume_24h = last_24_hours['sv'].sum()
    transactions_24h = last_24_hours['tc'].sum()
    buy_transactions_24h = last_24_hours['b'].sum()
    sell_transactions_24h = last_24_hours['s'].sum()

    peak_price_24h = last_24_hours['h'].max()
    peak_mcap_24h = Decimal(peak_price_24h) * total_supply

    low_price_24h = last_24_hours['h'].min()
    low_mcap_24h = Decimal(low_price_24h) * total_supply

    current_price = df.iloc[-1]['h']
    mcap = current_price * total_supply

    peak_price_all = df['h'].max()
    peak_mcap_all = Decimal(peak_price_all) * token.get_total_supply('Ether')
    peak_price_time = df[df['h'] == peak_price_all].iloc[0]['ts_utc']

    reserves = token.get_reserves()
    liquidity = common.eth_usd(reserves['weth'], 'Wei')

    # package results into json
    results = {
        "trends": trends,
        "24h_stats": {
            "volume": volume_24h,
            "buy_volume": buy_volume_24h,
            "sell_volume": sell_volume_24h,
            "transactions": transactions_24h,
            "buy_transactions": buy_transactions_24h,
            "sell_transactions": sell_transactions_24h,
            "peak_price": peak_price_24h,
            "peak_mcap": peak_mcap_24h,
            "low_price": low_price_24h,
            "low_mcap": low_mcap_24h,
        },
        "current_price": current_price,
        "mcap": mcap,
        "peak_price_all": peak_price_all,
        "peak_mcap_all": peak_mcap_all,
        "peak_price_time": peak_price_time,
        "liquidity": liquidity,
    }

    return {'image': img, 'analytics': results}

def format_numeric_value(value):
    if isinstance(value, Decimal):
        value = float(value)
    
    suffixes = ['K', 'M', 'B']
    suffix_idx = 0
    while abs(value) >= 1000 and suffix_idx < len(suffixes) - 1:
        value /= 1000.0
        suffix_idx += 1
    return f"${value}{suffixes[suffix_idx]}"

def format_analytics(data):
    trends = data['trends']
    stats_24h = data['24h_stats']

    trend_str = '\n'.join([f"{trend}: {value}%" for trend, value in trends.items()])
    stats_str = '\n'.join([f"📊 {stat.capitalize().replace('_', ' ')}: {value}" for stat, value in stats_24h.items()])

    analytics = f"""
    📈 Trends:
    {trend_str}
    
    📊 24h Stats:
    {stats_str}

    🔝 Peak Price (All Time): {format_numeric_value(data['peak_price_all'])} at {data['peak_price_time']}
    🔝 Peak Mcap (All Time): {format_numeric_value(data['peak_mcap_all'])}
    
    💰 Current Price: {format_numeric_value(data['current_price'])}
    💼 Market Cap: {format_numeric_value(data['mcap'])}
    
    💧 Liquidity: {format_numeric_value(data['liquidity'])}
    """

    return analytics

def analyse_pair(pair_address):
    result = {}
    pair_universe = get_pair_universe()
    pair_id = get_uniswap_pair_id(pair_universe,
                                  pair_address)

    df = get_candles(pair_id, "15m")
    logging.info("Got candles")

    # add a column with ts in utc timezone
    #df['ts_utc'] = pd.to_datetime(df['ts'], unit='s')

    predicted_data = predict(df, 30, "15min", "ts_utc", "c")

    # render
    img = render(df, predicted_data, "72 hours")
    result['img'] = img

    last_24_hours = df[df['ts'] > (df.iloc[-1]['ts'] - 86400)]

    volume_24h = last_24_hours['v'].sum()
    buy_volume_24h = last_24_hours['bv'].sum()
    sell_volume_24h = last_24_hours['sv'].sum()

    transactions_24h = last_24_hours['tc'].sum()
    buy_transactions_24h = last_24_hours['b'].sum()
    sell_transactions_24h = last_24_hours['s'].sum()

    peak_price = df['h'].max()
    peak_price_time = df[df['h'] == peak_price].iloc[0]['ts_utc']

    analytics = f"""
    📊 Volume (24h): ${volume_24h/1000}K
    📈 Buy Volume (24h): ${buy_volume_24h/1000}K
    📉 Sell Volume (24h): ${sell_volume_24h/1000}K
    🔄 Transactions (24h): {transactions_24h:.0f}
    📈 Buy Transactions (24h): {buy_transactions_24h:.0f}
    📉 Sell Transactions (24h): {sell_transactions_24h:.0f}
    🔝 Peak Price: {peak_price:.2e} $ at {peak_price_time}
    """

    result['analytics'] = analytics
    return result

logging.basicConfig(level=logging.INFO)
bot = Bot(config("BOT_TOKEN"))
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello!")

@dp.message(Command('pair'))
async def cmd_pair(message: types.Message, command: CommandObject):
    if command.args:
        pair_address = command.args
        analysis = analyse_pair(pair_address)
        graph_bytes = analysis['img']
        caption = analysis['analytics']

        await message.answer_photo(
            BufferedInputFile(
                graph_bytes.read(),
                filename="graph.jpg"
            ),
            caption=caption
        )

@dp.message(Command('ca'))
async def cmd_ca(message: types.Message, command: CommandObject):
    if command.args:
        ca = str(command.args)
        analysis = analyse_ca(ca)

        graph_bytes = analysis['image']
        caption = format_analytics(analysis['analytics'])

        await message.answer_photo(
            BufferedInputFile(
                graph_bytes.read(),
                filename="graph.jpg"
            ),
            caption=caption
        )


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

