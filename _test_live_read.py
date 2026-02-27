"""게임 중 리플레이 파일 실시간 읽기 테스트.

사용법:
  1. 스타크래프트에서 게임을 시작한다
  2. 이 스크립트를 실행한다:
     python _test_live_read.py "C:\...\replay.rep"
  3. 결과를 확인한다:
     - 읽기 성공 + 파일 크기 증가 → 실시간 읽기 가능
     - 읽기 실패 (PermissionError) → 파일 잠금됨
     - 파일 크기 변화 없음 → 게임 종료 후에만 기록됨
"""
import sys
import time
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        # 인자가 없으면 리플레이 폴더에서 가장 최근 .rep 파일을 자동 탐색
        print("사용법: python _test_live_read.py <리플레이 파일 경로>")
        print("  또는: python _test_live_read.py <리플레이 폴더 경로>")
        print()
        print("스타크래프트 게임 중에 실행하세요.")
        return

    target = Path(sys.argv[1])

    # 폴더가 주어지면 가장 최근 .rep 파일 찾기
    if target.is_dir():
        reps = sorted(target.glob("*.rep"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not reps:
            print(f"폴더에 .rep 파일 없음: {target}")
            return
        target = reps[0]
        print(f"최신 리플레이 파일: {target.name}")

    if not target.exists():
        print(f"파일 없음: {target}")
        return

    print(f"파일: {target}")
    print(f"2초 간격으로 파일 크기를 확인합니다. (Ctrl+C로 중단)\n")

    prev_size = None
    try:
        while True:
            try:
                size = target.stat().st_size
                # 읽기 시도
                with open(target, "rb") as f:
                    data = f.read(64)  # 처음 64바이트만 읽기
                status = "OK (읽기 성공)"
            except PermissionError:
                size = -1
                status = "LOCKED (읽기 불가)"
            except Exception as e:
                size = -1
                status = f"ERROR: {e}"

            change = ""
            if prev_size is not None and size >= 0:
                diff = size - prev_size
                if diff > 0:
                    change = f" (+{diff} bytes, 실시간 기록 중!)"
                elif diff == 0:
                    change = " (변화 없음)"
                else:
                    change = f" ({diff} bytes)"

            print(f"  크기: {size:>10,} bytes  |  {status}{change}")
            prev_size = size if size >= 0 else prev_size
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n중단됨.")


if __name__ == "__main__":
    main()
