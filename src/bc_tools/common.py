import decimal
from web3 import Web3
from print_color import print
import json
import requests
from decouple import config


import logging
import colorlog

def common_setup_logger():
    logger = logging.getLogger('common_logger')
    logger.setLevel(logging.DEBUG)

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

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger
common_logger = common_setup_logger()

def connect_web3():
    rpc = config('RPC')

    web3 = Web3(Web3.HTTPProvider(rpc))
    if web3.is_connected():
        #print(f'Connected to RPC', color='green', tag='Web3')
        return web3
    else:
        print(f'Failed to connect to RPC', color='red', tag='Web3')
        exit(1)

def get_abi(address):
    etherscan_api_key = config('ETHERSCAN_API_KEY')

    resp = requests.get(f'https://api.etherscan.io/api?module=contract&action=getabi&address={address}&apikey={etherscan_api_key}').json()
    if resp['status'] == '1':
        return resp['result']

def is_good_tx(txn_receipt) -> bool:
    return int(txn_receipt.status) == 1

def get_gas_used(txn_receipt, unit='Ether') -> float:
    gas_used = int(txn_receipt.gasUsed)
    return Web3.from_wei(gas_used, unit)

def tx_url(txhash):
    try:
        if type(txhash) == str:
            return f'{blockexp}tx/{txhash}'
        else:
            return f'{blockexp}tx/{Web3.to_hex(txhash)}'
    except Exception as e:
        return "txurl FAILED"

def cast(_value, _type, _ishex=False):
    try:
        if _ishex:
            if _type == 'address':
                return Web3.to_checksum_address(hexstr=_value)
            elif _type == 'bool':
                return Web3.to_int(hexstr=_value) != 0
            elif 'int' in _type:
                return int.from_bytes(_value, byteorder='big')
            elif 'bytes' in _type:
                return Web3.to_bytes(hexstr=_value)
            else:
                print(f'Unknown type: {_type}, returning {type(_value)}', color='red', tag='Cast')
                return _value
        else:
            if _type == 'address':
                return Web3.to_checksum_address(_value)
            elif _type == 'bool':
                return bool(_value in ['True', 'true', '1', 't', 'T'])
            elif 'int' in _type:
                return Web3.to_int(text=_value)
            elif 'bytes' in _type:
                return Web3.to_bytes(text=_value)
            else:
                print(f'Unknown type: {_type}, returning {type(_value)}', color='red', tag='Cast')
                return _value
            
    except Exception as e:
        print(f'Failed to cast {_value} to {_type}', color='red', tag='Cast')
        return _value

def get_chain_info(web3):
    chain_id = web3.eth.chain_id
    chains = requests.get('https://chainid.network/chains.json').json()

    for chain in chains:
        if chain['chainId'] == chain_id:
            return chain

def eth_usd(amount, unit='Wei'):
    
    one_eth = _eth_usd()
    wei_amount = Web3.to_wei(amount, unit)
    eth_amount = Web3.from_wei(wei_amount, "Ether")

    price = eth_amount * decimal.Decimal(one_eth)
    return price

def _eth_usd():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "ethereum",
            "vs_currencies": "usd"
        }

        response = requests.get(url, params=params)
        data = response.json()

        if response.status_code == 200:
            eth_to_usd = data.get("ethereum", {}).get("usd")
            if eth_to_usd is not None:
                return eth_to_usd
            else:
                raise ValueError("Failed to fetch the exchange rate data.")
        else:
            raise ValueError(f"Failed to fetch data. Status code: {response.status_code}")
    except requests.RequestException as e:
        raise ValueError(f"Error occurred during the request: {e}")
   
def setup_logger():
    # Create a logger
    logger = logging.getLogger('unisnipe')
    logger.setLevel(logging.DEBUG)  # Set the logging level

    # Create a file handler
    handler = logging.FileHandler('run.log')

    # Create a formatter and add it to the handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(handler)

    return logger

if __name__ == "__main__":
    web3 = connect_web3()
    chain_info = get_chain_info(web3)

    print(f'Connected to {chain_info["name"]}', color='green', tag='Web3')
    print(f'Block explorer: {chain_info["explorers"][0]["url"]}', color='green', tag='Web3')

