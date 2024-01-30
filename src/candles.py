from collections import defaultdict
import io
import requests
import jsonlines
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from decouple import config

from print_color import print

import logging
logging.basicConfig(level=logging.DEBUG)

API_URL = "https://tradingstrategy.ai/api"
API_KEY = config("TS_API_KEY") 

UNISWAP_V2_EXCHANGE_ID = 1
ETHEREUM_MAINNET_CHAIN_ID = 1

session = requests.Session()
session.headers.update({'Authorization': API_KEY})

def get_json_response(api_path, params=None):
    """
    Get a json response from the TradingStrategy.ai API.
    @param api_path: str : the api path to get the json response from
    @param params: dict : the parameters to pass to the api
    """
    url = f"{API_URL}/{api_path}"
    response = session.get(url, params=params)
    return response.json()

def get_exchange_universe():
    """
    Get the exchange_universe json.
    """
    return get_json_response("exchange-universe")

def get_pair_universe(fname=None):
    """
    Get the pair_universe dataframe.
    @param fname: str : the filename to save the pair_universe to
    """
    url = f"{API_URL}/pair-universe"
    response = session.get(url, stream=True)
    data = io.BytesIO(response.content)
    table = pq.read_table(data)

    if fname:
        table.to_pandas().to_csv(fname)

    return table.to_pandas()

def get_uniswap_pair_id(pair_universe, pair_address):
    """
    Get the pair_id for a given pair_address on Uniswap v2 on Ethereum mainnet.
    @param pair_universe: pd.DataFrame : the pair_universe dataframe
    @param pair_address: str : the pair contract address to get the pair_id for
    """
    pair_entry = np.where(
        (pair_universe['address'] == pair_address) &
        (pair_universe['exchange_id'] == UNISWAP_V2_EXCHANGE_ID) &
        (pair_universe['chain_id'] == ETHEREUM_MAINNET_CHAIN_ID)
    )

    pair_entry = pair_universe.iloc[pair_entry]
    print(pair_entry, color="yellow")

    return pair_entry['pair_id'].values[0]

def get_candles(pair_id,
                time_bucket,
                start_time=None,
                end_time=None,
                fname=None):
    """
    Get candles for a given pair_id and time_bucket.
    @param pair_id: int : the pair_id to get candles for
    @param time_bucket: str : the interval of the candles (1m, 5m, 15m, 1h, etc.)
    @param start_time: unix_epoch : the start time of the candles
    @param end_time: unix_epoch : the end time of the candles
    @param fname: str : the filename to save the candles to
    """
    url = f"{API_URL}/candles-jsonl"

    params = {
        "pair_ids": str(pair_id),
        "time_bucket": time_bucket
    }

    if start_time:
        params['start_time'] = start_time
    if end_time:
        params['end_time'] = end_time

    resp = session.get( url,
                        params=params,
                        stream=True)


    reader = jsonlines.Reader(resp.raw)
    print(resp.raw)

    candle_data = defaultdict(list)

    for idx, item in enumerate(reader):
        for key, value in item.items():
            candle_data[key].append(value)

    df = pd.DataFrame.from_dict(candle_data)
    
    # add a column with ts in utc timezone
    df['ts_utc'] = pd.to_datetime(df['ts'], unit='s')

    if fname:
        df.to_csv(fname)

    return df
