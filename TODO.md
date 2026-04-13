# StarRecord TODO

## 진행 현황 (2026-03-12)

### ✅ 완료된 작업

#### 게임 시작 시 Overlay 알림 (LastReplay.rep 기반)
- `config.py` — `last_replay_path`, `game_start_overlay` 설정 키 추가 + `get_last_replay_path()` 자동 탐색 헬퍼
- `watcher.py` — `LastReplayWatcher` 클래스 추가 (1초 폴링, 파일 크기 감소 = 새 게임 감지)
- `sc_replay_parser.py` — `parse_header_only()` 추가 (첫 번째 zlib 블록만 읽어 플레이어 정보 빠르게 추출)
- `main.py` — `make_game_start_callback()` + `cmd_daemon`에 `LastReplayWatcher` 연동
- `_test_lastreplay_watch.py` — 통합 테스트 스크립트로 업데이트

**동작 흐름:**
```
게임 시작 → LastReplay.rep 크기 감소 감지 (1초 폴링)
  → 2초 대기 (파일이 어느 정도 채워질 때까지)
  → parse_header_only() 로 플레이어 이름/종족 추출
  → DB 에서 상대방 전적 조회
  → tkinter overlay 팝업 (화면 우상단, 5초)
```

**실행 방법:**
```bash
# 테스트
python _test_lastreplay_watch.py

# 실제 사용
python main.py daemon
```

---

## 🔲 남은 작업

### 1. 실제 게임 테스트 및 튜닝
- [ ] 스타크래프트 실행 후 게임 시작 → overlay 팝업 표시 여부 확인
- [ ] `LAST_REPLAY_READ_DELAY` 튜닝 필요 (현재 2초)
  - 너무 빠르면 파일이 아직 헤더를 다 안 써서 파싱 실패
  - 너무 느리면 overlay가 너무 늦게 뜸
- [ ] `parse_header_only()` 파싱 실패 시 재시도 로직 고려
  - 현재: 실패하면 그냥 스킵
  - 개선안: 1~2초 후 재시도 (N회)

### 2. overlay 품질 개선
- [ ] 종족(`race`) 정보가 현재 `Unknown`으로 나오는 경우 개선
  - `parse_header_only()`는 파일명 기반 종족 추출인데 `LastReplay.rep`는 파일명이 항상 `LastReplay.rep`이라 종족 파싱 불가
  - 해결: CHK 맵 데이터(OWNR 섹션) 에서 종족 읽기 or 게임 종료 후 실제 리플레이에서 보완
- [ ] overlay 표시 시간 설정 (`config.json`의 `overlay_duration` 키)
- [ ] overlay 위치 설정 (현재 하드코딩: 화면 우상단 20px 여백)

### 3. `replay_dir` 설정 안내 개선
- [ ] `config.json`에 `replay_dir`이 비어있어 `daemon` 모드 실행 시 경고 발생
  - 스타크래프트 리플레이 폴더를 자동 탐색하는 로직 추가
  - `LastReplay.rep` 위치에서 폴더를 역추론 가능

### 4. 스타크래프트 경로 자동 설정
- [ ] `config.json`의 `starcraft_path`가 비어있음
  - `launcher.find_starcraft_path()` 결과를 `config.json`에 자동 저장

### 5. 장기 개선 과제
- [ ] 1v1 이외의 게임 형식(팀전 등) 플레이어 파싱 지원
- [ ] overlay에 맵 이름 표시 (CHK 파일에서 읽기)
- [ ] `_test_lastreplay_watch.py`를 실행하면 파일 크기를 줄여서 시뮬레이션하는 `--simulate` 옵션 추가

---

## config.json 현재 상태

```json
{
  "replay_dir": "",           ← 설정 필요 (리플레이 폴더 경로)
  "starcraft_path": "",       ← 설정 필요 (StarCraft.exe 경로)
  "my_names": ["kimsabuho"],  ← 설정 완료
  "notify_mode": "overlay",   ← 설정 완료
  "game_start_overlay": true, ← 설정 완료
  "last_replay_path": ""      ← 비워두면 자동 탐색 (현재 자동 탐색 성공)
}
```

`replay_dir`, `starcraft_path` 설정:
```bash
python main.py set-replay-dir "C:\Users\jaisung choi\Documents\StarCraft\Maps\Replays"
python main.py set-sc-path "C:\Program Files (x86)\StarCraft\StarCraft.exe"
```
