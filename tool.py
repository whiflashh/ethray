#!/usr/bin/env python3
import time
from web3 import Web3

RPC_URL = "http://localhost:8545"
POOL_CONFIGURATOR = "0x80C4cdee95E52a8ad2C57eC3265Bea3A9c91669D"
MIN_SUPPLY = 1e6

# 시그니처
RESERVE_INIT_SIG = Web3.keccak(text="ReserveInitialized(address,address,address,address,address)").hex()
RDU_SIG = Web3.keccak(text="ReserveDataUpdated(address,uint256,uint256,uint256,uint256,uint256)").hex()

# ABI
ATOKEN_ABI = [
    {"inputs":[],"name":"totalSupply","outputs":[{"type":"uint256","name":""}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"symbol","outputs":[{"type":"string","name":""}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"decimals","outputs":[{"type":"uint8","name":""}],"stateMutability":"view","type":"function"},
]

w3 = Web3(Web3.HTTPProvider(RPC_URL))
markets = {}
last_block = 0

def decode_address(topic):
    return Web3.to_checksum_address("0x" + topic.hex()[-40:])

def check_new_markets(from_block, to_block):
    try:
        logs = w3.eth.get_logs({
            "address": POOL_CONFIGURATOR,
            "fromBlock": from_block,
            "toBlock": to_block,
            "topics": ["0x" + RESERVE_INIT_SIG]
        })
        print(logs)
        
        for log in logs:
            print(log)
            asset = decode_address(log["topics"][1])
            atoken = decode_address(log["topics"][2])
            
            contract = w3.eth.contract(address=atoken, abi=ATOKEN_ABI)
            symbol = contract.functions.symbol().call()
            decimals = contract.functions.decimals().call()
            
            markets[atoken] = {
                "asset": asset,
                "symbol": symbol,
                "decimals": decimals,
                "start_block": log["blockNumber"]
            }
            print(f"New market: {symbol} ({atoken})")
    except Exception as e:
        print(f"Error checking new markets: {e}")

def check_liquidity(block_num):
    for atoken, market in list(markets.items()):
        try:
            contract = w3.eth.contract(address=atoken, abi=ATOKEN_ABI)
            total_supply = contract.functions.totalSupply().call(block_identifier=block_num)
            supply_units = total_supply / (10 ** market["decimals"])
            
            if supply_units < MIN_SUPPLY:
                print(f"LOW LIQUIDITY: {market['symbol']} supply={supply_units:.2f} < {MIN_SUPPLY}")
                
        except Exception as e:
            print(f"Error checking {market['symbol']}: {e}")

def main():
    global last_block
    
    current_block = w3.eth.block_number
    last_block = current_block - 5
        
    print("Starting liquidity monitor...")
    
    while True:
        try:
            current_block = w3.eth.block_number
            safe_block = current_block - 5

            print(f"current block : {current_block}")
            
            if safe_block > last_block:
                check_new_markets(last_block + 1, safe_block)
                check_liquidity(safe_block)
                last_block = safe_block
                
            time.sleep(3)
            
        except KeyboardInterrupt:
            print("Stopping...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
