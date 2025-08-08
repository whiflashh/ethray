#!/bin/bash
set -e

if ! pgrep -x "anvil" > /dev/null; then
  echo "anvil is not running."
  exit 1
fi

forge script script/GenerateInternalCallTx.s.sol:GenerateInternalCallTx \
  --rpc-url http://127.0.0.1:8545 \
  --broadcast -vv \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
