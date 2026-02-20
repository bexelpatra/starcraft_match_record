"""런처 모듈. 스타크래프트 실행 감지 및 동시 실행을 담당한다.

두 가지 모드를 제공한다:
  - launch: 스타크래프트와 리플레이 감시를 동시에 시작
  - daemon: 백그라운드에서 스타크래프트 프로세스를 감시하다가 자동으로 감시 시작/중지
"""

import subprocess
import time
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# 스타크래프트 프로세스 이름 (대소문자 무관하게 비교)
SC_PROCESS_NAMES = {"starcraft.exe", "starcraft remastered.exe"}

# 프로세스 확인 주기 (초)
POLL_INTERVAL = 5


def find_starcraft_path() -> Path | None:
    """스타크래프트 실행 파일을 자동으로 찾는다. 일반적인 설치 경로를 탐색."""
    common_paths = [
        Path("C:/Program Files (x86)/StarCraft/StarCraft.exe"),
        Path("C:/Program Files/StarCraft/StarCraft.exe"),
        Path("C:/Program Files (x86)/StarCraft Remastered/StarCraft.exe"),
        Path("D:/StarCraft/StarCraft.exe"),
        Path("D:/Games/StarCraft/StarCraft.exe"),
    ]
    for p in common_paths:
        if p.exists():
            log.info("스타크래프트 발견: %s", p)
            return p
    return None


def is_starcraft_running() -> bool:
    """스타크래프트 프로세스가 실행 중인지 확인한다.
    외부 패키지 없이 tasklist 명령어를 사용한다.
    """
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10,
        )
        lines = result.stdout.lower()
        return any(name in lines for name in SC_PROCESS_NAMES)
    except Exception as e:
        log.debug("프로세스 확인 실패: %s", e)
        return False


def launch_starcraft(sc_path: Path) -> subprocess.Popen | None:
    """스타크래프트를 실행한다. 프로세스 객체를 반환."""
    if not sc_path.exists():
        log.error("스타크래프트 경로를 찾을 수 없습니다: %s", sc_path)
        return None

    log.info("스타크래프트 실행: %s", sc_path)
    try:
        proc = subprocess.Popen(
            [str(sc_path)],
            cwd=str(sc_path.parent),
        )
        return proc
    except OSError as e:
        log.error("스타크래프트 실행 실패: %s", e)
        return None


def launch_mode(sc_path: Path, replay_dir: Path, on_new_replay) -> None:
    """런처 모드: 스타크래프트와 리플레이 감시를 동시에 시작한다.

    Args:
        sc_path: 스타크래프트 실행 파일 경로
        replay_dir: 리플레이 폴더 경로
        on_new_replay: 새 리플레이 콜백 (Path) -> None
    """
    from watcher import ReplayWatcher

    # 리플레이 감시 시작 (백그라운드 스레드)
    watcher = ReplayWatcher(replay_dir, on_new_replay)
    watcher.start()
    log.info("리플레이 감시 시작됨")

    # 스타크래프트 실행
    proc = launch_starcraft(sc_path)
    if proc is None:
        watcher.stop()
        return

    print("스타크래프트가 실행되었습니다.")
    print("게임이 끝나면 자동으로 전적을 알려드립니다.")
    print("스타크래프트를 종료하면 이 프로그램도 함께 종료됩니다.\n")

    try:
        # 스타크래프트 종료 대기
        # Battle.net 런처 경유 시 프로세스가 바로 끝날 수 있으므로
        # 프로세스 종료 후에도 실제 게임이 실행중인지 확인
        proc.wait()
        log.info("런처 프로세스 종료됨, 게임 프로세스 확인 중...")

        # 게임이 실제로 실행중일 수 있으므로 프로세스 감시
        while is_starcraft_running():
            time.sleep(POLL_INTERVAL)

        log.info("스타크래프트 종료 감지")
    except KeyboardInterrupt:
        log.info("사용자 종료 요청")
    finally:
        watcher.stop()
        print("\n감시 종료. 수고하셨습니다!")


def daemon_mode(replay_dir: Path, on_new_replay, on_sc_start=None, on_sc_stop=None) -> None:
    """데몬 모드: 백그라운드에서 스타크래프트 실행을 감시한다.

    스타크래프트가 실행되면 리플레이 감시를 시작하고,
    종료되면 감시를 중지한다. 이를 반복한다.

    Args:
        replay_dir: 리플레이 폴더 경로
        on_new_replay: 새 리플레이 콜백 (Path) -> None
        on_sc_start: 스타크래프트 시작 시 콜백 (선택)
        on_sc_stop: 스타크래프트 종료 시 콜백 (선택)
    """
    from watcher import ReplayWatcher

    print("StarRecord 데몬 모드 시작")
    print(f"리플레이 폴더: {replay_dir}")
    print("스타크래프트 실행을 감시하고 있습니다...")
    print("종료: Ctrl+C\n")

    watcher = None
    sc_was_running = False

    try:
        while True:
            sc_running = is_starcraft_running()

            if sc_running and not sc_was_running:
                # 스타크래프트가 방금 시작됨
                log.info("스타크래프트 실행 감지!")
                print("[*] 스타크래프트 감지 - 리플레이 감시 시작")

                watcher = ReplayWatcher(replay_dir, on_new_replay)
                watcher.start()

                if on_sc_start:
                    on_sc_start()

            elif not sc_running and sc_was_running:
                # 스타크래프트가 방금 종료됨
                log.info("스타크래프트 종료 감지")
                print("[*] 스타크래프트 종료 - 리플레이 감시 중지")

                if watcher:
                    watcher.stop()
                    watcher = None

                if on_sc_stop:
                    on_sc_stop()

                print("[*] 스타크래프트 실행을 다시 감시하고 있습니다...\n")

            sc_was_running = sc_running
            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        log.info("데몬 종료 요청")
    finally:
        if watcher:
            watcher.stop()
        print("\nStarRecord 데몬 종료. 수고하셨습니다!")
