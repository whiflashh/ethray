def parse_trace(trace):
    calls = []
    
    def extract(data, depth=0):
        if isinstance(data, dict):
            calls.append({
                'type': data.get('type', ''),
                'from': data.get('from', ''),
                'to': data.get('to', ''),
                'value': data.get('value', '0x0'),
                'gas_used': int(data.get('gasUsed', '0x0'), 16),
                'input': data.get('input', ''),
                'output': data.get('output', ''),
                'depth': depth
            })
            
            # 하위 calls 재귀 처리
            if 'calls' in data:
                for call in data['calls']:
                    extract(call, depth + 1)
    
    extract(trace)
    return calls

# 테스트
if __name__ == "__main__":
    sample_trace = {"from": "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266", "gas": "0x3335", "gasUsed": "0x857d", "to": "0xcf7ed3acca5a467e9e704c703e8d87f634fb0fc9", "input": "0x4e7fe0eb", "calls": [{"from": "0xcf7ed3acca5a467e9e704c703e8d87f634fb0fc9", "gas": "0x1f63", "gasUsed": "0x1ac3", "to": "0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0", "input": "0x281dfe7c", "calls": [{"from": "0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0", "gas": "0xbf6", "gasUsed": "0x267", "to": "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512", "input": "0x13f88d9b", "type": "STATICCALL"}], "type": "STATICCALL"}], "value": "0x0", "type": "CALL"}
    
    calls = parse_trace(sample_trace)
    print(f"Found {len(calls)} calls:")
    for i, call in enumerate(calls):
        print(f"{i+1}. {call['type']} (depth {call['depth']}) - Gas: {call['gas_used']:,}")