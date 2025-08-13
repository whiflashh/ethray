import requests

RPC_URL = "http://127.0.0.1:8545"


def rpc_call(method, params):
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    res = requests.post(RPC_URL, json=payload)
    res.raise_for_status()
    data = res.json()
    if "error" in data:
        raise Exception(f"RPC Error: {data['error']}")
    return data.get("result")


def get_tx_receipt(tx_hash: str) -> dict:
    result = rpc_call("eth_getTransactionReceipt", [tx_hash])
    return {
        "transactionHash": result["transactionHash"],
        "status": int(result["status"], 16),
        "from": result["from"],
        "to": result["to"],
        "gasUsed": int(result["gasUsed"], 16)
    }


def get_debug_trace(tx_hash: str) -> dict:
    trace_result = rpc_call("debug_traceTransaction", [tx_hash, {"tracer":"callTracer","timeout":"30s","reexec":1000000}])
    return trace_result
