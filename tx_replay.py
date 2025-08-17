from web3 import Web3

# 네트워크 연결
original_w3 = Web3(Web3.HTTPProvider("https://dimensional-convincing-pool.sei-pacific.quiknode.pro/2ef5d5d83795635834a0e0aa65b182f0c8ad1729"))
anvil_w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))

tx_hash = "0xb841865c0aa4146e8f68d4d0f1c31a5ee10fc91c6334e095d82eff19c2d8249f"

# 원본 트랜잭션 가져오기
tx = original_w3.eth.get_transaction(tx_hash)
from_address = tx['from']

print(f"Original tx: {tx_hash}")
print(f"From: {from_address}")
print(f"To: {tx['to']}")
print(f"Value: {original_w3.from_wei(tx['value'], 'ether')} ETH")
print(f"Gas: {tx['gas']:,}")
print(f"Nonce: {tx['nonce']}")

# 계정 impersonate
anvil_w3.manager.request_blocking("anvil_impersonateAccount", [from_address])

# 계정에 ETH 지급
balance_hex = hex(anvil_w3.to_wei(1000, 'ether'))
anvil_w3.manager.request_blocking("anvil_setBalance", [from_address, balance_hex])

nonce = anvil_w3.eth.get_transaction_count(from_address)
print(f"New nonce: {nonce}")

tx_params = {
    "from": from_address,
    "to": tx['to'],
    "value": tx['value'],
    "gas": tx['gas'],
    "gasPrice": tx['gasPrice'],
    "data": tx['input'],
    "nonce": nonce
}

try:
    estimated_gas = anvil_w3.eth.estimate_gas(tx_params)
    print(f"Estimated gas: {estimated_gas:,}")
    if estimated_gas > tx_params['gas']:
        print(f"WARNING: Original gas ({tx_params['gas']:,}) might be insufficient")
except Exception as e:
    print(f"Gas estimation failed: {e}")

# 트랜잭션 전송
try:
    new_tx_hash = anvil_w3.eth.send_transaction(tx_params)
    print(f"Sent transaction: {new_tx_hash.hex()}")
    
    receipt = anvil_w3.eth.wait_for_transaction_receipt(new_tx_hash)
    print(f"Status: {'Success' if receipt.status == 1 else 'Failed'}")
    print(f"Gas used: {receipt.gasUsed:,}")
    print(f"Block: {receipt.blockNumber}")
    
    replayed_tx = anvil_w3.eth.get_transaction(new_tx_hash)
    print(f"\n=== Verification ===")
    print(f"Original data: {tx['input'].hex()[:50]}...")
    print(f"Replayed data: {replayed_tx['input'].hex()[:50]}...")
    print(f"Data match: {'O' if tx['input'] == replayed_tx['input'] else 'X'}")
    print(f"Value match: {'O' if tx['value'] == replayed_tx['value'] else 'X'}")
    print(f"To match: {'O' if tx['to'] == replayed_tx['to'] else 'X'}")
    
except Exception as e:
    print(f"Transaction failed: {e}")

# impersonate 정리
anvil_w3.manager.request_blocking("anvil_stopImpersonatingAccount", [from_address])
