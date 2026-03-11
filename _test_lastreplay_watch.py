"""LastReplay.rep 파일 크기 변화 감지 → 알림 테스트.

새 게임이 시작되면 스타크래프트가 LastReplay.rep을 업데이트하므로
파일 크기가 변경되는 시점을 감지해 알림을 띄운다.

사용법:
    python _test_lastreplay_watch.py
"""

import sys
import time
import os
import io
from pathlib import Path

# Windows 콘솔 한글 깨짐 방지
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))

import config
from notifier import notify

# 감시 대상 파일
REPLAY_PATH = Path(r"C:\Users\jaisung choi\Documents\StarCraft\Maps\Replays\LastReplay.rep")

# 폴링 주기 (초)
POLL_INTERVAL = 2


def main():
    cfg = config.load()
    print(f"감시 대상: {REPLAY_PATH}")

    if not REPLAY_PATH.exists():
        print(f"[오류] 파일을 찾을 수 없습니다: {REPLAY_PATH}")
        print("스타크래프트를 한 번 실행해 LastReplay.rep 파일을 생성해주세요.")
        return

    prev_size = REPLAY_PATH.stat().st_size
    print(f"초기 파일 크기: {prev_size:,} bytes")
    print(f"{POLL_INTERVAL}초 간격으로 감시 중... (Ctrl+C로 종료)\n")

    try:
        while True:
            time.sleep(POLL_INTERVAL)

            try:
                cur_size = REPLAY_PATH.stat().st_size
            except OSError as e:
                print(f"[경고] 파일 접근 실패: {e}")
                continue

            if cur_size != prev_size:
                diff = cur_size - prev_size
                sign = "+" if diff > 0 else ""
                print(f"[변화 감지] {prev_size:,} → {cur_size:,} bytes ({sign}{diff:,})")

                notify(
                    "StarRecord - 변화 감지",
                    f"LastReplay.rep 크기 변경: {sign}{diff:,} bytes",
                    opponents=[{"name": "테스트 상대", "race": "T", "record": "알림 동작 확인"}],
                    cfg=cfg,
                )

                prev_size = cur_size
            else:
                print(f"  변화 없음: {cur_size:,} bytes")

    except KeyboardInterrupt:
        print("\n감시 종료.")


if __name__ == "__main__":
    main()
