#!/usr/bin/env python3
import os
import time
import json
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Set, Tuple

from web3 import Web3

RPC_HTTP = os.getenv("RPC_HTTP", "https://dimensional-convincing-pool.sei-pacific.quiknode.pro/2ef5d5d83795635834a0e0aa65b182f0c8ad1729")
POOL_CONFIGURATORS: List[str] = json.loads(os.getenv("POOL_CONFIGURATORS_JSON", '["0x80C4cdee95E52a8ad2C57eC3265Bea3A9c91669D"]'))

CONFIRMATIONS = int(os.getenv("CONFIRMATIONS", "5"))
WATCH_WINDOW_BLOCKS = int(os.getenv("WATCH_WINDOW_BLOCKS", "1000"))

USE_SCALED = os.getenv("USE_SCALED", "1") == "1"
USE_TOTAL  = os.getenv("USE_TOTAL", "1") == "1"
USE_TVL    = os.getenv("USE_TVL",   "0") == "1"

MIN_SCALED = float(os.getenv("MIN_SCALED", "1e6"))
MIN_TOTAL  = float(os.getenv("MIN_TOTAL",  "1e6"))
MIN_TVL_UNITS = float(os.getenv("MIN_TVL_UNITS", "0.5"))

CHECK_MINTER_CONC = os.getenv("CHECK_MINTER_CONC", "1") == "1"
MINTER_CONC_BLOCKS = int(os.getenv("MINTER_CONC_BLOCKS", "50"))
MAX_MINTERS = int(os.getenv("MAX_MINTERS", "1"))

RES_INIT_SIG = ("0x"+(Web3.keccak(text="ReserveInitialized(address,address,address,address,address)").hex()))
RDU_SIG      = ("0x"+(Web3.keccak(text="ReserveDataUpdated(address,uint256,uint256,uint256,uint256,uint256)").hex()))
TRANSFER_SIG = ("0x"+(Web3.keccak(text="Transfer(address,address,uint256)").hex()))

IATOKEN_ABI = [
    {"inputs":[],"name":"scaledTotalSupply","outputs":[{"type":"uint256","name":""}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"totalSupply","outputs":[{"type":"uint256","name":""}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"decimals","outputs":[{"type":"uint8","name":""}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"symbol","outputs":[{"type":"string","name":""}],"stateMutability":"view","type":"function"},
]

w3 = Web3(Web3.HTTPProvider(RPC_HTTP, request_kwargs={"timeout": 30}))

def cs(a:str)->str:
    return Web3.to_checksum_address(a)

def topic_addr(a:str)->str:
    return "0x" + "0"*24 + a.lower().replace("0x","")

@dataclass
class Market:
    asset: str
    aToken: str
    start_block: int
    symbol: str = "aToken"
    decimals: int = 18
    last_index: Optional[int] = None
    minters: Set[str] = field(default_factory=set)

@dataclass
class State:
    last_scanned: int = 0
    markets: Dict[str, Market] = field(default_factory=dict)

state = State()

def decode_address_topic(topic_bytes) -> str:
    return cs("0x" + topic_bytes.hex()[-40:])

def parse_reserve_initialized(log) -> Tuple[str,str,int,str]:
    asset  = decode_address_topic(log["topics"][1])
    aToken = decode_address_topic(log["topics"][2])
    blk    = log["blockNumber"]
    txh    = log["transactionHash"].hex()
    return asset, aToken, blk, txh

def parse_rdu_liquidity_index(log) -> int:
    data = log["data"]
    if data.startswith("0x"): data = data[2:]
    words = [int(data[i:i+64], 16) for i in range(0, len(data), 64)]
    if len(words) < 5:
        raise ValueError("RDU data too short")
    liquidityIndex = words[3]
    return liquidityIndex

def ensure_market(asset:str, aToken:str, blk:int):
    if aToken in state.markets: 
        return
    m = Market(asset=asset, aToken=aToken, start_block=blk)
    c = w3.eth.contract(address=cs(aToken), abi=IATOKEN_ABI)
    try:
        m.symbol = c.functions.symbol().call(block_identifier=blk)
    except: pass
    try:
        m.decimals = c.functions.decimals().call(block_identifier=blk)
    except: pass
    state.markets[aToken] = m
    print(f"[+] Watch market: asset={asset} aToken={aToken} sym={m.symbol} dec={m.decimals} @blk {blk}")

def get_scaled(aToken:str, block_num:int)->int:
    c = w3.eth.contract(address=cs(aToken), abi=IATOKEN_ABI)
    return int(c.functions.scaledTotalSupply().call(block_identifier=block_num))

def get_total(aToken:str, block_num:int)->int:
    c = w3.eth.contract(address=cs(aToken), abi=IATOKEN_ABI)
    return int(c.functions.totalSupply().call(block_identifier=block_num))

def compute_tvl_units(aToken:str, index:int, block_num:int)->float:
    scaled = get_scaled(aToken, block_num)
    return (scaled * index) / 1e27

def process_range(fr:int, to:int):
    logs = []
    for cfg in POOL_CONFIGURATORS:
        try:
            l = w3.eth.get_logs({
                "address": cs(cfg),
                "fromBlock": fr,
                "toBlock": to,
                "topics": [RES_INIT_SIG]
            })
            logs.extend(l)
        except Exception as e:
            print(f"[warn] get_logs ReserveInitialized {cfg} {fr}-{to}: {e}")
    for lg in logs:
        try:
            asset, aToken, blk, txh = parse_reserve_initialized(lg)
            ensure_market(asset, aToken, blk)
        except Exception as e:
            print(f"[warn] parse ReserveInitialized : {e}")

    for aToken, m in list(state.markets.items()):
        if to > m.start_block + WATCH_WINDOW_BLOCKS:
            print(f"[-] Stop watch {aToken} ({m.symbol}) — window expired @blk {to}")
            state.markets.pop(aToken, None)
            continue

        index_for_window = None
        if USE_TVL:
            try:
                rdu_logs = w3.eth.get_logs({
                    "fromBlock": max(fr, m.start_block),
                    "toBlock": to,
                    "topics": [RDU_SIG, topic_addr(m.asset)]
                })
                if rdu_logs:
                    idx = parse_rdu_liquidity_index(rdu_logs[-1])
                    m.last_index = idx
                    index_for_window = idx
            except Exception as e:
                print(f"[warn] RDU fetch for asset {m.asset} : {e}")

        risk_reasons = []
        try:
            if USE_SCALED:
                scaled = get_scaled(aToken, to)
                if scaled < MIN_SCALED:
                    risk_reasons.append(f"scaledTotalSupply({scaled}) < {MIN_SCALED}")
            if USE_TOTAL:
                total = get_total(aToken, to)
                total_units = total / (10 ** m.decimals)
                if total_units < MIN_TOTAL:
                    risk_reasons.append(f"totalSupply({total_units:.8f}) < {MIN_TOTAL}")
            if USE_TVL and index_for_window:
                tvl_units = compute_tvl_units(aToken, index_for_window, to)
                if tvl_units < MIN_TVL_UNITS:
                    risk_reasons.append(f"TVL({tvl_units:.8f}) < {MIN_TVL_UNITS}")
        except Exception as e:
            print(f"[warn] supply/TVL fetch {aToken} : {e}")

        if CHECK_MINTER_CONC and (to - m.start_block) >= MINTER_CONC_BLOCKS:
            try:
                mints = w3.eth.get_logs({
                    "fromBlock": m.start_block,
                    "toBlock": to,
                    "address": cs(aToken),
                    "topics": [TRANSFER_SIG, "0x" + "0"*64]
                })
                minters: Set[str] = set()
                for ev in mints:
                    to_addr = decode_address_topic(ev["topics"][2])
                    minters.add(to_addr)
                m.minters = minters
                if len(minters) <= MAX_MINTERS:
                    risk_reasons.append(f"minters<= {MAX_MINTERS} (unique={len(minters)})")
            except Exception as e:
                print(f"[warn] minter scan {aToken}: {e}")

        if risk_reasons:
            print(f"[ALERT] blk {to} aToken={aToken} ({m.symbol}) reasons: {', '.join(risk_reasons)}")

def main():
    if not POOL_CONFIGURATORS:
        raise SystemExit("Set POOL_CONFIGURATORS_JSON env var")
    head = w3.eth.block_number
    safe = head - CONFIRMATIONS
    state.last_scanned = safe
    print(f"[*] Live low-liquidity monitor")
    while True:
        try:
            head = w3.eth.block_number
            print(head)
            safe = head - CONFIRMATIONS
            if safe > state.last_scanned:
                fr = state.last_scanned + 1
                to = safe
                process_range(fr, to)
                state.last_scanned = safe
            time.sleep(2.5)
        except KeyboardInterrupt:
            print("Bye")
            break
        except Exception as e:
            print(f"[warn] loop error : {e}")
            time.sleep(2.5)

if __name__ == "__main__":
    main()

