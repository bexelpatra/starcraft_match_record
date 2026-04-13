# StarRecord 사용 매뉴얼

스타크래프트 1:1 전적을 자동으로 기록하고, 게임 시작/종료 시 상대 전적을 오버레이로 표시하는 도구.

---

## 1. 설치

### 1-1. 사전 요구사항

- **Python 3.12+** (https://www.python.org/downloads/)
  - 설치 시 반드시 "Add Python to PATH" 체크
- **Git** (https://git-scm.com/downloads)

### 1-2. 소스 다운로드

```powershell
git clone https://github.com/bexelpatra/starcraft_match_record.git
cd starcraft_match_record
```

### 1-3. 의존성 설치

```powershell
pip install -r requirements.txt
```

### 1-4. (선택) exe 빌드

Python 없이 exe로 실행하고 싶다면:

```powershell
pip install pyinstaller

# GUI 포함 단일 exe 빌드 (콘솔 창 숨김)
pyinstaller --onefile --windowed --name StarRecord main.py
```

빌드 완료 후 `dist/StarRecord.exe`가 생성된다.

**exe 더블클릭 → GUI 설정 화면이 바로 뜬다.**
닉네임, 리플레이 폴더, SC 경로를 GUI에서 설정하고 바로 실행할 수 있다.

CLI를 쓰고 싶으면 cmd에서 `StarRecord.exe daemon` 등으로 실행하면 된다.

---

## 2. 초기 설정

### 2-1. 본인 닉네임 등록

```powershell
python main.py set-name "내닉네임"
```

여러 닉네임을 사용한다면 각각 등록한다.

### 2-2. 스타크래프트 경로 설정

```powershell
python main.py set-sc-path "C:\Program Files (x86)\StarCraft\StarCraft.exe"
```

### 2-3. 리플레이 폴더 설정

```powershell
python main.py set-replay-dir "C:\Users\내이름\Documents\StarCraft\Maps\Replays"
```

### 2-4. 기존 리플레이 가져오기

이미 쌓인 리플레이가 있다면 일괄 등록:

```powershell
python main.py import "C:\Users\내이름\Documents\StarCraft\Maps\Replays"
```

---

## 3. 실행 모드

### 3-1. Daemon 모드 (권장)

백그라운드에서 스타크래프트 프로세스를 감시하다가, 게임이 감지되면 자동으로 리플레이 감시를 시작한다.

```powershell
python main.py daemon
```

또는 `StarRecord_Daemon.bat`을 더블클릭.

**동작 흐름:**
1. 프로그램 시작 → 스타크래프트 프로세스 대기
2. 스타크래프트 실행 감지 → 리플레이 폴더 감시 시작 + toast 알림
3. 게임 시작 → LastReplay.rep 변화 감지 → 상대 전적 오버레이 표시
4. 게임 종료 → 리플레이 파싱 → 전적 기록 + 알림
5. 스타크래프트 종료 → 감시 중지 → 다시 대기

종료: `Ctrl+C`

### 3-2. Launch 모드

스타크래프트를 직접 실행하면서 동시에 리플레이 감시를 시작한다.

```powershell
python main.py launch
```

또는 `StarRecord_Launcher.bat`을 더블클릭.

### 3-3. Watch 모드

특정 폴더만 직접 감시한다 (daemon 없이):

```powershell
python main.py watch "C:\...\Replays"
```

### 3-4. GUI 모드

설정 변경, 전적 조회, 실행을 GUI에서 할 수 있다.

```powershell
python main.py gui
```

---

## 4. 전적 조회

### 특정 상대 전적

```powershell
python main.py record "상대닉네임"
```

### 전체 전적 요약

```powershell
python main.py records
```

출력 예시:
```
상대                    승    패    합계   최근 대전
-------------------------------------------------------
HM_sSak                 12     8    20   2026-04-10
MiniMaxii                5     3     8   2026-04-08
```

---

## 5. 메모 기능

상대에 대한 메모를 남길 수 있다. 게임 시작/종료 알림에 메모가 함께 표시된다.

### CLI로 메모 관리

```powershell
# 메모 조회
python main.py memo "상대닉네임"

# 메모 추가
python main.py memo "상대닉네임" add "초반 러시 주의, 더블넥서스 잘 감"

# 메모 전체 삭제
python main.py memo "상대닉네임" clear
```

### 게임 중 채팅으로 메모 (daemon/watch 모드에서)

리플레이에 기록된 채팅 메시지로도 메모를 남길 수 있다:
- 게임 중 채팅: `!memo 초반 러시 주의` → 상대에게 메모 저장
- 게임 중 채팅: `!memo clear` → 상대 메모 삭제

---

## 6. 별칭 관리

같은 사람이 닉네임을 바꿔가며 플레이하는 경우:

```powershell
python main.py alias "원래닉네임" "새닉네임"
```

등록 후 "새닉네임"의 전적이 "원래닉네임"에 합산된다.

---

## 7. 알림 모드

`config.json`의 `notify_mode` 값으로 알림 방식을 변경할 수 있다:

| 값 | 설명 |
|----|------|
| `toast` | Windows 알림 센터 토스트 (기본값) |
| `overlay` | 항상 위 반투명 오버레이 팝업 |
| `both` | toast + overlay 동시 |

```json
{
  "notify_mode": "overlay"
}
```

---

## 8. 설정 파일 (config.json)

최초 실행 시 자동 생성된다. 수동 편집도 가능하다.

```json
{
  "replay_dir": "C:\\Users\\...\\Replays",
  "starcraft_path": "C:\\...\\StarCraft.exe",
  "db_path": "star_record.db",
  "my_names": ["내닉네임"],
  "auto_detect_me": true,
  "watch_interval_seconds": 2,
  "notify_on_new_game": true,
  "notify_mode": "toast",
  "last_replay_path": "",
  "game_start_overlay": true
}
```

| 키 | 설명 |
|----|------|
| `replay_dir` | 리플레이 저장 폴더 |
| `starcraft_path` | StarCraft.exe 경로 |
| `my_names` | 본인 닉네임 목록 |
| `notify_mode` | 알림 방식 (`toast` / `overlay` / `both`) |
| `last_replay_path` | LastReplay.rep 경로 (비어있으면 자동 탐색) |
| `game_start_overlay` | 게임 시작 시 오버레이 표시 여부 |

---

## 9. 파일 구조

```
starcraft_match_record/
  main.py                  CLI 진입점
  gui.py                   GUI 화면
  config.py                설정 관리
  config.json              사용자 설정 (자동 생성)
  db.py                    SQLite DB (전적, 메모)
  star_record.db           DB 파일 (자동 생성)
  record_manager.py        리플레이 파싱 + 전적 처리
  sc_replay_parser.py      .rep 파일 파서
  watcher.py               폴더/파일 감시
  launcher.py              스타크래프트 실행 감지
  notifier.py              알림 (toast/overlay)
  StarRecord_Launcher.bat  Launch 모드 바로가기
  StarRecord_Daemon.bat    Daemon 모드 바로가기
  requirements.txt         Python 의존성
```

---

## 10. 문제 해결

### "리플레이 폴더가 설정되지 않았습니다"
→ `python main.py set-replay-dir "경로"` 실행

### "스타크래프트 경로를 찾을 수 없습니다"
→ `python main.py set-sc-path "경로"` 실행

### 게임 시작 오버레이가 안 뜸
→ `config.json`에서 `game_start_overlay`가 `true`인지 확인
→ `last_replay_path`가 올바른지 확인 (보통 `리플레이폴더/LastReplay.rep`)

### 한글 깨짐
→ 터미널에서 `chcp 65001` 실행 후 재시도 (bat 파일에는 이미 포함)

### exe 빌드 시 config.json을 못 찾음
→ exe와 같은 폴더에 `config.json`을 복사하거나, 한 번 실행하면 자동 생성됨
