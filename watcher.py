"""리플레이 폴더 감시 모듈.

두 가지 감시 방식을 제공한다:
  - ReplayWatcher     : watchdog 기반, 새 .rep 파일 생성/수정 감지 (게임 종료 후)
  - LastReplayWatcher : 폴링 기반, LastReplay.rep 크기 변화 감지 (게임 시작 시)
"""

import threading

import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

log = logging.getLogger(__name__)

# 리플레이 파일이 완전히 쓰여지기까지 대기하는 시간 (초)
SETTLE_DELAY = 3.0


class ReplayHandler(FileSystemEventHandler):
    """새 .rep 파일이 생성되거나 수정되면 콜백을 호출한다."""

    def __init__(self, on_new_replay):
        """
        Args:
            on_new_replay: 새 리플레이가 감지되면 호출되는 콜백.
                           시그니처: on_new_replay(replay_path: Path) -> None
        """
        super().__init__()
        self._on_new_replay = on_new_replay
        self._processed = set()

    def on_created(self, event: FileCreatedEvent):
        if not event.is_directory:
            self._handle(event.src_path)

    def on_modified(self, event: FileModifiedEvent):
        if not event.is_directory:
            self._handle(event.src_path)

    def _handle(self, filepath: str):
        path = Path(filepath)

        if path.suffix.lower() != ".rep":
            return

        # 같은 파일을 중복 처리하지 않는다
        if path.name in self._processed:
            return

        # 파일이 완전히 쓰여질 때까지 잠시 대기
        log.info("새 리플레이 감지: %s (%.1f초 대기)", path.name, SETTLE_DELAY)
        time.sleep(SETTLE_DELAY)

        # 파일 크기가 0이면 아직 쓰는 중일 수 있음
        if path.stat().st_size == 0:
            log.debug("파일 크기 0, 스킵: %s", path.name)
            return

        self._processed.add(path.name)

        try:
            self._on_new_replay(path)
        except Exception as e:
            log.error("리플레이 처리 실패: %s - %s", path.name, e)


class ReplayWatcher:
    """리플레이 폴더를 감시하고, 새 파일이 생기면 콜백을 호출한다."""

    def __init__(self, replay_dir: Path, on_new_replay):
        """
        Args:
            replay_dir: 감시할 디렉토리 경로.
            on_new_replay: 새 리플레이 콜백. (Path) -> None
        """
        self.replay_dir = replay_dir
        self.handler = ReplayHandler(on_new_replay)
        self.observer = Observer()

    def start(self):
        """감시를 시작한다 (비동기, 백그라운드 스레드)."""
        self.observer.schedule(self.handler, str(self.replay_dir), recursive=True)
        self.observer.start()
        log.info("리플레이 폴더 감시 시작: %s", self.replay_dir)

    def stop(self):
        """감시를 중지한다."""
        self.observer.stop()
        self.observer.join()
        log.info("리플레이 폴더 감시 중지")

    def run_forever(self):
        """메인 스레드를 블록하며 감시한다. Ctrl+C로 종료."""
        self.start()
        try:
            while self.observer.is_alive():
                self.observer.join(timeout=1)
        except KeyboardInterrupt:
            log.info("종료 요청 감지")
        finally:
            self.stop()


# ── LastReplay.rep 감시 ────────────────────────────────────────

# 게임 시작 감지 후 헤더 파싱 전 대기 시간 (초)
# 너무 짧으면 파일이 아직 유효한 데이터를 안 가질 수 있음
LAST_REPLAY_READ_DELAY = 2.0

# 폴링 주기 (초)
LAST_REPLAY_POLL_INTERVAL = 1.0


class LastReplayWatcher:
    """LastReplay.rep 파일 크기를 폴링하여 새 게임 시작을 감지한다.

    스타크래프트는 새 게임이 시작되면 LastReplay.rep 파일을
    처음부터 다시 쓰기 시작한다. 따라서:
      - 파일 크기가 줄어드는 순간 = 새 게임 시작
      - 크기가 처음으로 증가하는 순간 = 게임이 기록 중

    Args:
        replay_path: LastReplay.rep 파일 경로
        on_game_start: 새 게임 감지 시 호출되는 콜백.
                       시그니처: on_game_start(replay_path: Path) -> None
        poll_interval: 폴링 주기 (초, 기본값 1.0)
        read_delay: 감지 후 파싱 전 대기 시간 (초, 기본값 2.0)
    """

    def __init__(
        self,
        replay_path: Path,
        on_game_start,
        poll_interval: float = LAST_REPLAY_POLL_INTERVAL,
        read_delay: float = LAST_REPLAY_READ_DELAY,
    ):
        self.replay_path = replay_path
        self._on_game_start = on_game_start
        self._poll_interval = poll_interval
        self._read_delay = read_delay
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """백그라운드 스레드에서 감시를 시작한다."""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="LastReplayWatcher",
            daemon=True,
        )
        self._thread.start()
        log.info("LastReplay.rep 감시 시작: %s", self.replay_path)

    def stop(self) -> None:
        """감시를 중지한다."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        log.info("LastReplay.rep 감시 중지")

    def _poll_loop(self) -> None:
        """폴링 루프 본체. 백그라운드 스레드에서 실행된다."""
        prev_size: int | None = None

        while not self._stop_event.is_set():
            try:
                cur_size = self._get_size()
            except OSError as e:
                log.debug("LastReplay.rep 접근 실패: %s", e)
                self._stop_event.wait(self._poll_interval)
                continue

            if prev_size is not None and cur_size is not None:
                # 크기가 줄었다 = 파일이 초기화됨 = 새 게임 시작
                if cur_size < prev_size:
                    log.info(
                        "새 게임 감지! LastReplay.rep 크기: %d → %d bytes",
                        prev_size, cur_size,
                    )
                    self._handle_game_start()

            if cur_size is not None:
                prev_size = cur_size

            self._stop_event.wait(self._poll_interval)

    def _get_size(self) -> int | None:
        """파일 크기를 반환한다. 파일이 없거나 접근 불가면 None."""
        try:
            return self.replay_path.stat().st_size
        except OSError:
            return None

    def _handle_game_start(self) -> None:
        """새 게임 시작을 처리한다."""
        # 파일이 어느 정도 채워질 때까지 대기
        log.debug("%.1f초 대기 후 헤더 읽기...", self._read_delay)
        self._stop_event.wait(self._read_delay)

        if self._stop_event.is_set():
            return

        try:
            self._on_game_start(self.replay_path)
        except Exception as e:
            log.error("게임 시작 콜백 실패: %s", e, exc_info=True)
