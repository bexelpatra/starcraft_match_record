# star_record - 세션 컨텍스트 (작업 이어가기용)

> 마지막 작업일: 2026-02-20
> 이 파일을 먼저 읽으면 이전 대화 맥락을 복원할 수 있다.

---

## 1. 프로젝트 한 줄 요약

스타크래프트 리플레이(.rep)를 자동 파싱하여 상대별 전적을 SQLite에 저장하고,
새 게임 시작 시 Windows 토스트 알림으로 전적을 보여주는 Python CLI 프로그램.

---

## 2. 현재 완료된 것 (Phase 1 전체 완료)

| 모듈 | 파일 | 상태 | 설명 |
|------|------|------|------|
| 리플레이 파서 | `sc_replay_parser.py` | 완료 | .rep 바이너리를 순수 Python으로 파싱 |
| 설정 | `config.py` | 완료 | config.json 로드/저장/기본값 |
| DB | `db.py` | 완료 | SQLite 스키마 + CRUD (players, games, aliases, chat) |
| 전적 관리 | `record_manager.py` | 완료 | 파싱→저장, 전적 조회, 닉네임 자동 추론 |
| 폴더 감시 | `watcher.py` | 완료 | watchdog 기반 .rep 파일 생성 감지 |
| 런처/데몬 | `launcher.py` | 완료 | SC 동시 실행(launch) + 프로세스 감시(daemon) |
| 알림 | `notifier.py` | 완료 | plyer 우선, PowerShell 폴백, 콘솔 최후 수단 |
| CLI | `main.py` | 완료 | 10개 서브커맨드 (import/watch/launch/daemon/record 등) |
| 바로가기 | `*.bat` 2개 | 완료 | Launcher, Daemon 더블클릭 실행 |

---

## 3. 현재 DB 상태

테스트용 리플레이 2개가 import됨:

```
players:
  id=1 YB_Scan       (is_me=0)
  id=2 awdfzxvczvccv12 (is_me=0)
  id=3 kimsabuho     (is_me=1)  ← 본인으로 등록됨
  id=4 MiniMaxii     (is_me=0)

games:
  id=1 YB_Scan vs awdfzxvczvccv12  | 승자 미확정 | my_result=unknown
  id=2 kimsabuho vs MiniMaxii      | kimsabuho 승 | my_result=win ← 소급 갱신 완료
```

### 해결된 버그
- ~~set-name 후 기존 게임 my_result 소급 미갱신~~ → `recalculate_my_results()` 추가로 해결
- ~~config.json에 starcraft_path 키 누락~~ → load() 시 DEFAULTS에서 자동 병합
- ~~콘솔 한글 깨짐~~ → main.py에서 `chcp 65001` + `sys.stdout` UTF-8 래핑

---

## 4. 아직 안 한 것 (Phase 2 + 잔여 작업)

### 즉시 할 수 있는 개선
- [ ] PyInstaller로 exe 패키징 테스트
- [ ] 실제 스타크래프트 리플레이 폴더로 watch/daemon 실전 테스트 (docs/test_scenarios.md 참조)

### Phase 2 (추후 기능)
- [ ] 오버레이 UI (게임 위에 표시, tkinter TOPMOST 방식 - POC 테스트 완료)
  - [ ] 오버레이에 최근 전적/맵/날짜 등 상세 정보 표시
  - [ ] 오버레이 표시 위치/크기/지속시간 사용자 설정 가능하게
  - [ ] notifier.py에 오버레이 방식 추가 (toast/overlay 선택 가능)
- [ ] 플레이어 메모 기능
  - [ ] DB에 player_memos 테이블 추가
  - [ ] CLI에서 메모 작성/조회 명령어
  - [ ] 오버레이에 상대 메모 표시
- [ ] 인게임 채팅 커맨드 (실시간 리플레이 읽기)
  - [ ] 게임 중 리플레이 파일 실시간 읽기 가능 여부 조사
  - [ ] 채팅 커맨드 파싱 (/info, /memo, /record 등)
  - [ ] 커맨드 감지 시 오버레이로 응답 표시
  - [ ] 커맨드로 플레이어 메모 실시간 작성
- [ ] 메모리 읽기로 로비 단계 상대 감지 (pymem)
- [ ] 계정-ID 매핑 (수동 alias는 구현됨, 메모리 기반은 미구현)
- [ ] 원격 DB 연동
- [ ] 통계 대시보드 (웹 또는 GUI)
- [ ] 시스템 트레이 아이콘 (데몬 모드에서)

---

## 5. 핵심 설계 결정 (변경 시 참고)

| 결정 | 내용 | 이유 |
|------|------|------|
| DB | SQLite | 설치 불필요, 원격 DB 마이그레이션 용이 |
| 감지 방식 | 파일 감시 (Option C) | 안전, 안정, 관리자 권한 불필요 |
| 알림 | 토스트 알림 | Phase 2에서 오버레이로 확장 예정 |
| 닉네임 | 자동추론 + 수동등록 | 빈도 기반 추론, 동률 시 수동 |
| 프로세스 감지 | tasklist 명령어 | 외부 패키지 없이 동작 |
| 패키징 | PyInstaller | 가장 대중적, 단일 exe |

---

## 6. 사용자 의도 & 배경

- 직접 플레이하는 것을 기반으로 제작
- 친구/일반 게이머가 간단하게 사용할 수 있어야 함
- 사용자는 스타크래프트를 주로 시청하며, 직접 플레이 경험은 적음
- 해킹 우려를 최소화해야 함 → 오픈소스, 관리자 권한 불필요, 파일 읽기만
- 향후 GitHub 공개 배포 고려 중
- 코드는 바이브코딩으로 유지보수할 예정 → 클린코드, 읽기 쉽게

---

## 7. 파일별 의존 관계

```
main.py (진입점)
├── config.py       (설정)
├── db.py           (DB)
├── record_manager.py (비즈니스 로직)
│   ├── sc_replay_parser.py (파서)
│   └── db.py
├── watcher.py      (파일 감시, watchdog 필요)
├── launcher.py     (런처/데몬)
│   └── watcher.py
└── notifier.py     (알림, plyer 선택적)
```

외부 패키지: `watchdog` (필수), `plyer` (선택, 없으면 PowerShell 폴백)

---

## 8. 폴더 구조

```
star_record/
├── main.py                  # CLI 진입점
├── config.py                # 설정 관리
├── db.py                    # SQLite DB
├── sc_replay_parser.py      # .rep 파서
├── record_manager.py        # 전적 관리 로직
├── watcher.py               # 폴더 감시
├── launcher.py              # 런처/데몬
├── notifier.py              # 알림
├── StarRecord_Launcher.bat  # 런처 바로가기
├── StarRecord_Daemon.bat    # 데몬 바로가기
├── requirements.txt         # 외부 패키지
├── config.json              # 사용자 설정 (자동 생성)
├── star_record.db           # DB 파일 (자동 생성)
├── docs/                    # 문서
│   ├── meta_info.md         # 프로젝트 명세서
│   └── session_context.md   # 이 파일
└── replays/                 # 테스트/샘플 리플레이
    └── samples/
        └── *.rep, *.json, *.txt
```

---

## 9. 테스트 방법

```bash
cd D:\pypy\star_record

# 샘플 리플레이 가져오기
python main.py import "D:\pypy\star_record\replays\samples"

# 전적 조회
python main.py records
python main.py record MiniMaxii

# 프로세스 감지 테스트
python -c "from launcher import is_starcraft_running; print(is_starcraft_running())"

# 데몬 모드 (Ctrl+C로 종료)
python main.py daemon
```

---

## 10. 참고 문서

- `docs/meta_info.md` - 프로젝트 전체 명세서 (DB 스키마, CLI 명령어, Phase 로드맵, 보안 등)
- `config.json` - 현재 설정 상태
- `star_record.db` - 현재 DB (SQLite, 테스트 데이터)
