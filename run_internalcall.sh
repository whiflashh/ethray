#!/bin/bash
set -e

RPC_URL="${RPC_URL:-http://127.0.0.1:8545}"

if ! pgrep -x "anvil" > /dev/null; then
  echo "anvil is not running."
  exit 1
fi

cd foundry
forge script script/GenerateInternalCallTx.s.sol:GenerateInternalCallTx \
  --rpc-url http://127.0.0.1:8545 \
  --broadcast -vv \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

SCRIPT_PATH="script/GenerateInternalCallTx.s.sol:GenerateInternalCallTx"
CHAIN_ID=$(cast chain-id --rpc-url "$RPC_URL")
BCAST_JSON="broadcast/$(basename "${SCRIPT_PATH%%:*}")/$CHAIN_ID/run-latest.json"
TX_HASH=$(jq -r '[.transactions[] | select(.transactionType=="CALL")] | last | .hash' "$BCAST_JSON")

echo "***"
echo "TX_HASH for test : $TX_HASH"
echo "***"
