# 테스트 매뉴얼

1. 다음 명령어를 실행
   ```bash
   anvil --fork-url https://dimensional-convincing-pool.sei-pacific.quiknode.pro/2ef5d5d83795635834a0e0aa65b182f0c8ad1729 --fork-block-number 118133643 --auto-impersonate
   ```
2. `tool.py` 실행
   ```bash
   python3 tool.py
   ```
3. `tx_replay.py` 실행
   ```bash
   python3 tx_replay.py
   ```
4. 테스트 완료 후 다시 테스트 필요 시 anvil 종료 후 위 과정 반복
