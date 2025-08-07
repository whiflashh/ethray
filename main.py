from tracker import get_tx_receipt, get_debug_trace
from parser import parse_trace
# from detector import detect_vulnerabilities
# from alert import send_alert

def main():
    tx_hash = input("tx hash : ")
    receipt = get_tx_receipt(tx_hash)
    trace = get_debug_trace(tx_hash)
    calls = parse_trace(trace)
    # alerts = detect_vulnerabilities(calls)
    # send_alert(alerts)
    print(calls)

if __name__ == "__main__":
    main()
