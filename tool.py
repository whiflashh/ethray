#!/usr/bin/env python3

import time
from web3 import Web3

RPC_URL = "http://localhost:8545"
POOL_CONFIGURATOR = "0x80C4cdee95E52a8ad2C57eC3265Bea3A9c91669D"
MIN_SUPPLY = 1.0

INIT_RESERVES_SELECTOR = "0x02fb45e6"
RESERVE_INIT_TOPIC = Web3.keccak(
    text="ReserveInitialized(address,address,address,address,address)"
).hex()

ATOKEN_ABI = [
    {"inputs":[],"name":"totalSupply","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"symbol","outputs":[{"type":"string"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"decimals","outputs":[{"type":"uint8"}],"stateMutability":"view","type":"function"},
]

w3 = Web3(Web3.HTTPProvider(RPC_URL))
to_cs = Web3.to_checksum_address
_seen = set()

def _trace(txh_hex: str):
    return w3.provider.make_request(
        "debug_traceTransaction",
        [txh_hex, {"tracer":"callTracer","timeout":"20s"}]
    )["result"]

def _has_init_reserves(txh_hex: str) -> bool:
    sel = INIT_RESERVES_SELECTOR.lower()
    target = POOL_CONFIGURATOR.lower()
    t = _trace(txh_hex)
    stack = [t]
    while stack:
        n = stack.pop()
        if str(n.get("to","")).lower() == target and str(n.get("input","")).lower().startswith(sel):
            return True
        for c in (n.get("calls") or n.get("children") or []):
            stack.append(c)
    return False

def _topic_addr(t) -> str:
    return to_cs("0x" + t.hex()[-40:])

def _handle_tx(txh_hex: str):
    rcpt = w3.eth.get_transaction_receipt(txh_hex)
    for lg in rcpt["logs"]:
        if not lg["topics"]: 
            continue
        if lg["topics"][0].hex().lower() != RESERVE_INIT_TOPIC.lower():
            continue
        asset  = _topic_addr(lg["topics"][1])
        atoken = _topic_addr(lg["topics"][2])
        print(f"[ReserveInitialized] asset={asset} aToken={atoken} block={lg['blockNumber']} tx={txh_hex}")
        try:
            c = w3.eth.contract(address=atoken, abi=ATOKEN_ABI)
            dec = c.functions.decimals().call()
            sym = c.functions.symbol().call()
            ts  = c.functions.totalSupply().call(block_identifier=lg["blockNumber"])
            su  = ts / (10 ** dec)
            tag = "⚠️ 취약" if su < MIN_SUPPLY else "OK"
            print(f"  -> {sym} totalSupply={su:.6f} ({tag})")
        except Exception as e:
            print(f"  -> aToken 조회 실패 : {e}")

def main():
    print("[i] start")
    while True:
        try:
            head = w3.eth.block_number
            print("current block :", head)
            start = max(0, head - 5)
            for b in range(start, head + 1):
                blk = w3.eth.get_block(b, full_transactions=True)
                for tx in blk.transactions or []:
                    txh = tx["hash"].hex()
                    if txh in _seen:
                        continue
                    _seen.add(txh)
                    try:
                        if _has_init_reserves(txh):
                            print(f"[HIT] initReserves in tx {txh} (block {b})")
                            _handle_tx(txh)
                    except Exception as e:
                        print(f"[trace err] {txh} : {e}")
            time.sleep(3)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("err :", e)
            time.sleep(3)

if __name__ == "__main__":
    main()

