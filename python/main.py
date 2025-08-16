import json

from tracker import get_tx_receipt, get_debug_trace
from parser import parse_trace
from discord_dm_bot import send_discord_alert


# from detector import detect_vulnerabilities
# from alert import send_alert

def main():
    tx_hash = input("tx hash : ")

    # receipt = get_tx_receipt(tx_hash)
    # print(json.dumps(receipt, indent=2))

    # trace = get_debug_trace(tx_hash)
    # print(json.dumps(trace, indent=2))

    # calls = parse_trace(trace)
    # print(json.dumps(calls, indent=2))
    # alerts = detect_vulnerabilities(calls)
    # send_alert(alerts)

    send_discord_alert(tx_hash)


if __name__ == "__main__":
    main()
