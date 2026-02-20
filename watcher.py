"""리플레이 폴더 감시 모듈. 새 .rep 파일을 감지하면 콜백을 호출한다."""

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
