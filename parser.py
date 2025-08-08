# from web3 import Web3
import json

def parse_trace(trace):
    """
    debug_traceCall 결과에서 internal call을 파싱
    
    (Args) trace (dict): debug_traceCall에서 받은 trace 데이터
    (Returns) list: 파싱된 internal call들의 리스트 """
    internal_calls = []
    
    def extract_calls(calls_data, depth=0):
        """
        재귀적으로 nested call들을 추출하는 내부 함수
        
        Args:
            calls_data: call 데이터 (dict 또는 list)
            depth (int): 현재 call의 깊이 (중첩 레벨)
        """
        if isinstance(calls_data, dict):  # calls_data가 딕셔너리인 경우 (단일 call)
            if 'calls' in calls_data:  # 'calls' 키가 있으면 하위 call들이 존재함 - 재귀 처리
                for call in calls_data['calls']:
                    extract_calls(call, depth + 1)  # 깊이 +1로 재귀 호출
            
            call_info = {                                     # 현재 call의 정보를 추출하여 저장
                'type': calls_data.get('type', ''),           # CALL, STATICCALL, DELEGATECALL 등
                'from': calls_data.get('from', ''),           # 호출자 주소
                'to': calls_data.get('to', ''),               # 피호출자 주소
                'value': calls_data.get('value', '0x0'),      # 전송된 ETH 양 (hex)
                'gas': calls_data.get('gas', '0x0'),          # 할당된 가스 (hex)
                'gasUsed': calls_data.get('gasUsed', '0x0'),  # 실제 사용된 가스 (hex)
                'input': calls_data.get('input', ''),         # 함수 호출 데이터 (함수 시그니처 + 파라미터)
                'output': calls_data.get('output', ''),       # 반환 데이터
                'depth': depth                                # call의 중첩 깊이
            }
            internal_calls.append(call_info)
            
        elif isinstance(calls_data, list):
            for call in calls_data: # calls_data가 리스트인 경우 (여러 call들)
                extract_calls(call, depth)  # 각 call을 재귀 처리
    
    extract_calls(trace, 0)  # 메인 call부터 시작
    return internal_calls

def format_call_info(call):
    """
    internal call 정보를 사람이 읽기 쉬운 형태로 포맷팅
    
    (Args) call (dict): 원본 call 정보  
    (Returns)dict: 포맷팅된 call 정보
    """
    return {
        'type': call['type'],
        'from': call['from'],
        'to': call['to'],
        
        'value_eth': Web3.from_wei(int(call['value'], 16), 'ether') if call['value'] != '0x0' else 0, # hex value를 ETH 단위로 변환 (0x0이면 0으로 처리)
        'gas_used': int(call['gasUsed'], 16) if call['gasUsed'] != '0x0' else 0, # hex gasUsed를 10진수로 변환
        'depth': call['depth'],
        'input_data': call['input'][:10] + '...' if len(call['input']) > 10 else call['input'] # input 데이터가 길면 앞 10자만 표시 (함수 시그니처 확인용)
    }

def decode_hex_string(hex_output):
    """
    ABI 인코딩된 hex output을 문자열로 디코딩 시도
    
    (Args) hex_output (str): hex 형태의 output 데이터  
    (Returns) str: 디코딩된 문자열 또는 원본 hex 데이터
    """
    try:
        if hex_output.startswith('0x'):
            hex_data = hex_output[2:]  # '0x' 접두사 제거
            
            # 표준 ABI string 인코딩은 최소 128자 (64자 offset + 64자 length + 데이터)
            if len(hex_data) >= 128:
                # 첫 64자 (32바이트)는 offset (보통 0x20 = 32)
                # 다음 64자 (32바이트)는 문자열 길이
                length = int(hex_data[64:128], 16)
                
                if length > 0 and length < 1000:
                    string_data = hex_data[128:128 + length * 2] # 실제 문자열 데이터 추출 (length * 2 = hex 문자 개수)
                    return bytes.fromhex(string_data).decode('utf-8', errors='ignore')  # hex를 바이트로 변환 후 UTF-8로 디코딩
    except Exception:
        pass
    return hex_output

def print_call_tree(calls, indent=0):
    """
    call tree를 계층구조로 시각화하여 출력
    
    Args:
        calls (list): 포맷팅된 call 정보들
        indent (int): 들여쓰기 레벨
    """
    for i, call in enumerate(calls):
        prefix = "  " * indent + f"├─ Call {i+1}:" # 트리 구조 시각화를 위한 접두사
        
        print(f"{prefix} {call['type']}")
        print(f"{'  ' * (indent+1)}From: {call['from']}")
        print(f"{'  ' * (indent+1)}To:   {call['to']}")
        print(f"{'  ' * (indent+1)}Gas Used: {call['gas_used']:,}")  # 천단위 콤마 추가
        print(f"{'  ' * (indent+1)}Value: {call['value_eth']} ETH")
        print(f"{'  ' * (indent+1)}Input: {call['input_data']}")
        
        if 'output' in call and call['output']:  # output이 있으면 디코딩 시도
            decoded = decode_hex_string(call['output'])
            
            if decoded != call['output']: # 디코딩 성공시에만 표시
                print(f"{'  ' * (indent+1)}Output (decoded): {decoded}")
        print()  # 빈 줄로 구분

def analyze_transaction_trace(w3, tx_hash):
    """
    실제 Web3를 사용하여 트랜잭션의 internal call 분석 (참고용)
    
    Args:
        w3: Web3 인스턴스
        tx_hash (str): 분석할 트랜잭션 해시
    (Returns) list: 포맷팅된 internal call 정보들
    """
    try:
        trace = w3.manager.request_blocking("debug_traceTransaction", [tx_hash, {"tracer": "callTracer"}]) # debug_traceTransaction RPC 호출하여 trace 데이터 가져오기
        internal_calls = parse_trace(trace) # internal calls 파싱
        formatted_calls = [format_call_info(call) for call in internal_calls] # 결과 포맷팅
        
        return formatted_calls
        
    except Exception as e:
        print(f"Error tracing transaction: {e}")
        return []

if __name__ == "__main__":
    # ===== 테스트용 실제 trace 데이터 =====
    sample_trace = {
        "from": "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266",
        "gas": "0x3335",     # 할당된 가스
        "gasUsed": "0x857d", # 실제 사용된 가스
        "to": "0xcf7ed3acca5a467e9e704c703e8d87f634fb0fc9",
        "input": "0x4e7fe0eb",  # 호출된 함수의 시그니처
        "output": "0x0000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000b706f6e672066726f6d2043000000000000000000000000000000000000000000",
        "calls": [  # 내부에서 발생한 호출들
            {
                "from": "0xcf7ed3acca5a467e9e704c703e8d87f634fb0fc9",
                "gas": "0x1f63",
                "gasUsed": "0x1ac3",
                "to": "0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0",
                "input": "0x281dfe7c",
                "output": "0x0000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000b706f6e672066726f6d2043000000000000000000000000000000000000000000",
                "calls": [  # 2차 중첩 호출
                    {
                        "from": "0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0",
                        "gas": "0xbf6",
                        "gasUsed": "0x267",
                        "to": "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512",
                        "input": "0x13f88d9b",
                        "output": "0x0000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000b706f6e672066726f6d2043000000000000000000000000000000000000000000",
                        "type": "STATICCALL"  # 상태를 변경하지 않는 읽기 전용 호출
                    }
                ],
                "type": "STATICCALL"
            }
        ],
        "value": "0x0",  # ETH 전송 없음
        "type": "CALL"   # 일반 호출
    }
    
    # ===== 분석 시작 =====
    print("=== Transaction Trace Analysis ===")
    print(f"Transaction Hash: 0x7bbef5946097e9875a20195d1f2af2770f567409117b831d3b4261522d626af1")
    print(f"From: {sample_trace['from']}")
    print(f"To: {sample_trace['to']}")
    print(f"Total Gas Used: {int(sample_trace['gasUsed'], 16):,}") # hex 가스 사용량을 10진수로 변환하여 표시
    print()
    
    # ===== Internal Calls 파싱 =====
    internal_calls = parse_trace(sample_trace)
    
    print(f"Found {len(internal_calls)} internal calls:")
    print()
    
    # ===== 포맷팅 및 출력 정보 준비 =====
    formatted_calls = []
    for call in internal_calls:
        formatted_call = format_call_info(call)
        formatted_call['output'] = call.get('output', '') # output 정보도 디코딩을 위해 추가
        formatted_calls.append(formatted_call)
    
    # ===== Call Tree 시각화 =====
    print_call_tree(formatted_calls)
    
    # ===== 통계 요약 =====
    print("=== Summary ===")
    call_types = {}  # call 타입별 개수 집계
    total_gas = 0    # 총 가스 사용량 집계
    
    for call in formatted_calls:
        call_type = call['type']
        call_types[call_type] = call_types.get(call_type, 0) + 1
        total_gas += call['gas_used']
    
    print(f"Total Internal Calls: {len(formatted_calls)}")
    print(f"Call Types: {call_types}")
    print(f"Total Gas Used in Internal Calls: {total_gas:,}")
    
    # ===== 메인 호출의 출력 디코딩 =====
    sample_output = sample_trace['output']
    decoded_output = decode_hex_string(sample_output)
    if decoded_output != sample_output:
        print(f"Main Output (decoded): '{decoded_output}'")
