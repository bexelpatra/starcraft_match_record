# StarRecord 아키텍처 문서

## 프로젝트 개요

StarCraft: Brood War / Remastered 리플레이를 자동 분석하여 상대별 전적을 관리하고, 게임 시작 시 실시간으로 알림을 제공하는 Windows 전적 관리 도구.

---

## 시스템 아키텍처

```
                         ┌──────────────┐
                         │  config.json │
                         └──────┬───────┘
                                │
                         ┌──────▼───────┐
                         │  config.py   │  설정 로드/저장
                         └──────┬───────┘
                                │
┌─────────┐   ┌─────────┐  ┌───▼───────────┐  ┌──────────────┐
│ .rep     │──▶│ watcher │──▶│   main.py     │──▶│ notifier.py  │
│ 리플레이 │   │  .py    │  │  (CLI 진입점) │  │  toast/overlay│
└─────────┘   └─────────┘  └───┬───────────┘  └──────────────┘
                                │
                         ┌──────▼───────────┐
                         │ record_manager.py │  파싱+전적 관리
                         └──────┬───────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼                       ▼
           ┌────────────────┐      ┌─────────────┐
           │sc_replay_parser│      │   db.py      │
           │     .py        │      │  (SQLite)    │
           └────────────────┘      └──────┬───────┘
                                          │
                                   ┌──────▼───────┐
                                   │ star_record.db│
                                   └──────────────┘
```

---

## 실행 모드

### `import` — 일괄 가져오기
```
python main.py import <리플레이_폴더>
```
지정 폴더의 모든 `.rep` 파일을 파싱하여 DB에 저장한다. 본인 닉네임 자동 추론도 수행.

### `watch` — 폴더 감시
```
python main.py watch <리플레이_폴더>
```
watchdog으로 폴더를 실시간 감시. 새 `.rep` 파일이 생기면 자동 파싱 → DB 저장 → 전적 알림.

### `launch` — 스타크래프트와 동시 실행
```
python main.py launch
```
스타크래프트를 실행하고 리플레이 폴더 감시를 동시에 시작. 스타크래프트 종료 시 함께 종료.

### `daemon` — 백그라운드 프로세스 감시
```
python main.py daemon
```
스타크래프트 프로세스를 주기적으로 확인. 실행되면 리플레이 감시를 시작하고, 종료되면 중지. 반복 동작.

### 기타 명령어
- `record <상대>` — 특정 상대 전적 조회
- `records` — 전체 상대별 전적 요약
- `set-name <닉네임>` — 본인 닉네임 수동 등록
- `set-sc-path <경로>` — StarCraft 실행 파일 경로 설정
- `set-replay-dir <경로>` — 리플레이 폴더 경로 설정
- `alias <원래이름> <별칭>` — 닉네임 별칭 등록

---

## 데이터 흐름

```
[.rep 파일]
    │
    ▼
[SCReplayParser]  바이너리 파싱 → game_info, players, map_data, chat, stats
    │
    ▼
[RecordManager.process_replay()]  데이터 가공 + 승패 판정
    │
    ▼
[Database]  games, game_players, chat_messages 테이블에 저장
    │
    ▼
[RecordManager.get_record()]  상대별 전적 조회
    │
    ▼
[notify()]  설정에 따라 toast / overlay / both 알림
```

---

## 모듈 구조

| 모듈 | 역할 |
|------|------|
| `main.py` | CLI 진입점. argparse로 명령어 라우팅. 콜백 팩토리 제공 |
| `config.py` | `config.json` 로드/저장. DEFAULTS 관리 |
| `db.py` | SQLite 래퍼. 스키마 초기화, CRUD, 전적 조회 쿼리 |
| `record_manager.py` | 리플레이 파싱→DB 저장, 전적 조회, 본인 닉네임 추론 |
| `sc_replay_parser.py` | `.rep` 바이너리 파서. 게임 정보, 플레이어, 맵, 채팅, 커맨드 추출 |
| `notifier.py` | 알림 모듈. toast(plyer/PowerShell), overlay(tkinter), 통합 API |
| `watcher.py` | watchdog 기반 폴더 감시. 새 `.rep` 파일 감지 시 콜백 호출 |
| `launcher.py` | 스타크래프트 실행/감지. launch 모드, daemon 모드 제공 |

### 의존 관계

```
main.py
  ├── config.py
  ├── db.py
  ├── record_manager.py
  │     ├── sc_replay_parser.py
  │     └── db.py
  ├── notifier.py
  ├── watcher.py (선택)
  └── launcher.py (선택)
        └── watcher.py
```

---

## DB 스키마

### players
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 자동 증가 |
| name | TEXT UNIQUE | 플레이어 이름 |
| is_me | INTEGER | 본인 여부 (0/1) |
| created_at | TEXT | 생성 시각 |

### aliases
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 자동 증가 |
| player_id | INTEGER FK | players.id 참조 |
| alt_name | TEXT UNIQUE | 별칭 이름 |

### games
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 자동 증가 |
| replay_file | TEXT UNIQUE | 리플레이 파일명 (중복 방지 키) |
| played_at | TEXT | 대전 시각 (파일명에서 추출) |
| duration_seconds | REAL | 게임 시간 (초) |
| duration_text | TEXT | 게임 시간 (텍스트) |
| map_name | TEXT | 맵 이름 |
| map_tileset | TEXT | 맵 타일셋 |
| game_type | TEXT | 게임 유형 (Melee 등) |
| winner_name | TEXT | 승자 이름 |
| loser_name | TEXT | 패자 이름 |
| winner_race | TEXT | 승자 종족 |
| loser_race | TEXT | 패자 종족 |
| my_result | TEXT | 본인 기준 결과 (win/loss/unknown) |
| parsed_at | TEXT | 파싱 시각 |

### game_players
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 자동 증가 |
| game_id | INTEGER FK | games.id 참조 |
| player_id | INTEGER FK | players.id 참조 |
| race | TEXT | 종족 |
| is_winner | INTEGER | 승자 여부 (0/1) |
| apm | REAL | 분당 액션 수 |

### chat_messages
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 자동 증가 |
| game_id | INTEGER FK | games.id 참조 |
| player_id | INTEGER FK | players.id 참조 |
| message | TEXT | 채팅 내용 |
| game_time | TEXT | 인게임 시간 |
| frame | INTEGER | 프레임 번호 |

---

## 알림 시스템

### 통합 API

```python
notify(title, message, opponents=None, cfg=None)
```

`config.json`의 `notify_mode`에 따라 알림 방식을 선택한다:

| notify_mode | 동작 |
|-------------|------|
| `"toast"` | Windows 토스트 알림만 표시 |
| `"overlay"` | tkinter 오버레이 팝업만 표시 (opponents 필요) |
| `"both"` | 토스트 + 오버레이 모두 표시 |

### Toast 알림 폴백 체인

```
plyer (설치 시) → PowerShell .ps1 파일 → 콘솔 출력
```

- **plyer**: 크로스플랫폼 알림 라이브러리. 설치되어 있으면 우선 사용.
- **PowerShell**: Windows 기본 Toast API. `$` 변수 소실 방지를 위해 임시 `.ps1` 파일로 실행.
- **콘솔**: 위 두 가지 모두 실패 시 콘솔에 텍스트 출력.

### Overlay 팝업

- tkinter TOPMOST 반투명 창으로 화면 오른쪽 상단에 표시
- 별도 데몬 스레드에서 실행 (메인 루프 블로킹 방지)
- 상대 수에 따라 높이 자동 조절
- 설정된 시간(기본 5초) 후 자동 닫힘

---

## 설정 (config.json)

| 키 | 타입 | 기본값 | 설명 |
|----|------|--------|------|
| `replay_dir` | string | `""` | 리플레이 폴더 경로 |
| `starcraft_path` | string | `""` | StarCraft 실행 파일 경로 |
| `db_path` | string | `"star_record.db"` | SQLite DB 파일 경로 |
| `my_names` | string[] | `[]` | 본인 닉네임 목록 |
| `auto_detect_me` | bool | `true` | import 시 본인 닉네임 자동 추론 |
| `watch_interval_seconds` | int | `2` | 폴더 감시 주기 (초) |
| `notify_on_new_game` | bool | `true` | 새 게임 시 알림 표시 여부 |
| `notify_mode` | string | `"toast"` | 알림 방식: `"toast"`, `"overlay"`, `"both"` |

---

## 향후 계획 (Phase 2)

- **인게임 채팅 커맨드**: 채팅으로 전적 조회 (`!record <상대>`)
- **메모 기능**: 상대별 메모 저장 (플레이 스타일, 주의점 등)
- **종족별 전적**: 상대 종족별 세부 승률 통계
- **APM 추세**: 게임별 APM 변화 그래프
- **웹 대시보드**: 브라우저에서 전적 조회 및 통계 시각화
- **ELO 레이팅**: 상대별 실력 추정치 계산
