# star_record - 프로젝트 명세서

## 프로젝트 개요
스타크래프트 BW/리마스터 리플레이를 자동 파싱하여 상대 전적을 관리하고,
게임 시작 시 상대방과의 전적을 실시간으로 알려주는 프로그램.

**대상 사용자**: 직접 플레이하는 게이머 (친구/일반 유저가 간단히 사용 가능하도록)

## 핵심 목표
- 리플레이 파일에서 상대 닉네임, 승패, 종족, 맵, 채팅 등을 추출
- 상대별 전적을 누적 저장
- 새 게임 시작 시 상대와의 전적을 자동 알림

---

## 기술 스택
- **언어**: Python 3.12+
- **DB**: SQLite (내장 sqlite3 모듈)
- **파일 감시**: watchdog 라이브러리
- **알림**: Windows 토스트 알림 (plyer 우선, PowerShell 폴백)
- **리플레이 파싱**: sc_replay_parser.py (자체 구현, 외부 의존성 없음)
- **패키징**: PyInstaller → 단일 exe 배포

## 아키텍처 결정사항

### DB 선택: SQLite
- 이유: 설치 불필요, 파일 1개 관리, SQL 쿼리 가능, 원격 DB 마이그레이션 용이
- DB 파일: `star_record.db`

### 상대 감지 방식: Option C (리플레이 폴더 감시)
- LastReplay.rep 또는 새 .rep 파일 생성을 감지
- 게임 시작 직후 1~2초 내 상대 정보 추출 가능
- 가장 안전하고 안정적 (메모리 읽기/패킷 스니핑 불필요)

### 알림 방식: Windows 토스트 알림 (Phase 1)
- Phase 2에서 오버레이 UI 추가 예정

### 본인 닉네임: 자동 추론 + 수동 등록
- 여러 리플레이에서 가장 많이 등장하는 이름 = 본인
- config에서 수동 등록도 가능

### 실행 방식: 런처 + 데몬 두 가지 모드 제공
- **런처 (launch)**: 스타크래프트와 리플레이 감시를 동시에 시작. SC 종료 시 함께 종료.
- **데몬 (daemon)**: 백그라운드 상주하며 SC 프로세스 감시. SC 시작/종료 자동 감지.

---

## DB 스키마

```sql
CREATE TABLE players (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    is_me       INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE aliases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id   INTEGER NOT NULL,
    alt_name    TEXT UNIQUE NOT NULL,
    created_at  TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
);

CREATE TABLE games (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    replay_file     TEXT UNIQUE NOT NULL,
    played_at       TEXT,
    duration_seconds REAL,
    duration_text   TEXT,
    map_name        TEXT,
    map_tileset     TEXT,
    game_type       TEXT,
    winner_name     TEXT,
    loser_name      TEXT,
    winner_race     TEXT,
    loser_race      TEXT,
    my_result       TEXT,  -- 'win', 'loss', 'unknown'
    parsed_at       TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE game_players (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL,
    player_id   INTEGER NOT NULL,
    race        TEXT,
    is_winner   INTEGER DEFAULT 0,
    apm         REAL,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
);

CREATE TABLE chat_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL,
    player_id   INTEGER NOT NULL,
    message     TEXT,
    game_time   TEXT,
    frame       INTEGER,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
);
```

---

## 파일 구조

```
star_record/
├── main.py                  # 진입점 (CLI)
├── config.py                # 설정 관리
├── db.py                    # SQLite DB 초기화 + CRUD
├── sc_replay_parser.py      # .rep 바이너리 파서
├── record_manager.py        # 전적 저장/조회/닉네임 추론
├── watcher.py               # 리플레이 폴더 실시간 감시
├── launcher.py              # 런처 + 데몬 모드
├── notifier.py              # Windows 토스트 알림
├── StarRecord_Launcher.bat  # 런처 바로가기
├── StarRecord_Daemon.bat    # 데몬 바로가기
├── requirements.txt         # 외부 패키지
├── config.json              # 사용자 설정 (자동 생성)
├── star_record.db           # SQLite DB (자동 생성)
├── docs/                    # 문서
│   ├── meta_info.md         # 이 문서
│   └── session_context.md   # 세션 컨텍스트
└── replays/                 # 리플레이
    └── samples/             # 테스트/샘플
```

---

## CLI 명령어

```bash
# 초기 설정
python main.py set-sc-path "C:\...\StarCraft.exe"    # SC 경로 설정
python main.py set-replay-dir "C:\...\Replays"        # 리플레이 폴더 설정
python main.py set-name <닉네임>                      # 본인 닉네임 등록

# 리플레이 가져오기
python main.py import <폴더경로>                       # 일괄 가져오기

# 실행 모드
python main.py launch                                  # SC와 함께 실행
python main.py daemon                                  # 백그라운드 프로세스 감시
python main.py watch <폴더경로>                        # 단순 폴더 감시

# 전적 조회
python main.py record <상대닉네임>                     # 특정 상대 전적
python main.py records                                 # 전체 상대별 전적

# 기타
python main.py alias <원래이름> <별칭>                  # 별칭 등록
```

---

## 동작 흐름

### 런처 모드 (launch)
```
사용자가 StarRecord_Launcher.bat 더블클릭
→ 리플레이 감시 시작 (백그라운드 스레드)
→ 스타크래프트 실행
→ 게임 종료 시 리플레이 감지 → 파싱 → DB 저장 → 전적 알림
→ 스타크래프트 종료 감지 → 프로그램 종료
```

### 데몬 모드 (daemon)
```
사용자가 StarRecord_Daemon.bat 더블클릭 (또는 Windows 시작프로그램 등록)
→ 5초 간격으로 StarCraft.exe 프로세스 확인
→ SC 시작 감지 → 리플레이 감시 ON + "감시 시작" 알림
→ 게임 종료 시 리플레이 감지 → 파싱 → DB 저장 → 전적 알림
→ SC 종료 감지 → 리플레이 감시 OFF + "감시 중지" 알림
→ 다시 SC 시작 대기... (반복)
```

---

## Phase 로드맵

### Phase 1 (완료)
- [x] 리플레이 파서 (sc_replay_parser.py)
- [x] SQLite DB 설계 + 구현 (db.py)
- [x] 설정 관리 (config.py)
- [x] 전적 관리 로직 (record_manager.py)
- [x] 리플레이 폴더 감시 (watcher.py)
- [x] 기존 리플레이 일괄 파싱 → DB 저장
- [x] 본인 닉네임 자동 추론
- [x] 전적 조회 기능
- [x] Windows 토스트 알림 (notifier.py)
- [x] CLI 진입점 (main.py)
- [x] 런처 모드 (launcher.py + bat)
- [x] 데몬 모드 (프로세스 자동 감시)

### Phase 2 (추후)
- [ ] 메모리 읽기로 로비 단계 상대 감지
- [ ] 오버레이 UI (게임 위에 표시)
- [ ] 계정-ID 매핑 (메모리 기반 또는 수동 alias)
- [ ] 원격 DB 연동
- [ ] 통계 대시보드 (웹 또는 GUI)
- [ ] PyInstaller exe 패키징 + 배포
- [ ] 시스템 트레이 아이콘

---

## 보안 & 신뢰

### 이 프로그램이 하는 일
- 리플레이 폴더의 .rep 파일을 **읽기만** 함 (Read-only)
- SQLite DB에 전적 저장 (로컬 파일)
- Windows 토스트 알림 표시

### 이 프로그램이 하지 않는 일
- 게임 프로세스 메모리 접근 안 함
- DLL 인젝션 안 함
- 네트워크 통신 안 함 (Phase 1)
- 관리자 권한 불필요
- 레지스트리 수정 안 함

### 사용자 신뢰 확보
- GitHub 오픈소스 공개 → 코드 검증 가능
- 관리자 권한 불필요 → UAC 팝업 없음
- Portable 실행 → 설치 불필요, 폴더에서 바로 실행
- VirusTotal 스캔 결과 첨부 (exe 배포 시)
- 동작 로그 투명 공개

---

## 인게임 정보 추출 메모 (Phase 2용)

### 메모리 읽기 (BW 1.16.1 알려진 주소)
```
플레이어 이름 배열: 0x0057EE9C (각 36바이트, 최대 8명)
플레이어 종족:     0x0057F1C0
게임 상태:         0x006D11C0
현재 맵 경로:      0x0057FD3C
```

### 리마스터(SCR) 참고사항
- 업데이트마다 주소 변동 → 패턴 스캔(시그니처 스캔) 필요
- pymem 또는 ctypes + ReadProcessMemory 사용
- 안티치트 감지 가능성 있음

### 채팅 입력 (SendInput)
- 기술적으로 가능하나 게임 조작 방해 → 비추천
- 오버레이 방식이 더 적합

---

## 리플레이 파일명 규칙
```
날짜@시간_플레이어1(종족)_vs_플레이어2(종족).rep
예: 2026-02-07@020624_kimsabuho(t)_vs_MiniMaxii(p).rep
종족 코드: t=Terran, z=Zerg, p=Protoss
```

## 설정 파일 (config.json) 구조
```json
{
    "replay_dir": "C:/Users/.../StarCraft/Replays",
    "starcraft_path": "C:/Program Files (x86)/StarCraft/StarCraft.exe",
    "db_path": "star_record.db",
    "my_names": ["kimsabuho"],
    "auto_detect_me": true,
    "watch_interval_seconds": 2,
    "notify_on_new_game": true
}
```

## 패키징 (PyInstaller)
```bash
pip install pyinstaller
pyinstaller --onefile --name StarRecord main.py
# 결과물: dist/StarRecord.exe
```
옵션: `--noconsole` (콘솔 숨김), `--icon=icon.ico` (아이콘)
