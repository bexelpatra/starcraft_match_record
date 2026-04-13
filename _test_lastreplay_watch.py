"""LastReplay.rep 파일 크기 변화 감지 → 헤더 파싱 → overlay 통합 테스트.

새 게임이 시작되면 스타크래프트가 LastReplay.rep을 처음부터 써서
파일 크기가 줄어든다. 이 시점을 감지해 헤더를 파싱하고 overlay를 띄운다.

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
from watcher import LastReplayWatcher
from db import Database
from record_manager import RecordManager


def make_test_callback(manager: RecordManager, cfg: dict):
    """테스트용 게임 시작 콜백."""
    from sc_replay_parser import SCReplayParser
    from notifier import notify

    def on_game_start(replay_path: Path):
        print(f"\n[게임 시작 감지] {replay_path.name}")
        print(f"  파일 크기: {replay_path.stat().st_size:,} bytes")

        # 헤더 파싱
        try:
            parser = SCReplayParser(str(replay_path))
            parser.parse_header_only()
            players = parser.players
            print(f"  플레이어: {[p['name'] for p in players]}")
        except Exception as e:
            print(f"  파싱 실패: {e}")
            players = []

        my_names = manager.my_names
        opponents_info = []

        for p in players:
            record = manager.get_record(p["name"])
            wins = record.get("wins", 0)
            losses = record.get("losses", 0)
            total = record.get("total", 0)
            record_str = "첫 대전" if total == 0 else f"{wins}승 {losses}패"
            is_me = "★ 나" if p["name"] in my_names else ""
            print(f"  - {p['name']} ({p.get('race','?')}) {record_str} {is_me}")
            if p["name"] not in my_names:
                opponents_info.append({
                    "name": p["name"],
                    "race": p.get("race", "?"),
                    "record": record_str,
                })

        # my_names 미설정시 전체 표시
        if not opponents_info:
            for p in players:
                record = manager.get_record(p["name"])
                wins = record.get("wins", 0)
                losses = record.get("losses", 0)
                total = record.get("total", 0)
                record_str = "첫 대전" if total == 0 else f"{wins}승 {losses}패"
                opponents_info.append({
                    "name": p["name"],
                    "race": p.get("race", "?"),
                    "record": record_str,
                })

        if opponents_info:
            notify(
                "StarRecord - 게임 시작",
                "",
                opponents=opponents_info,
                cfg={**cfg, "notify_mode": "overlay"},
            )

    return on_game_start


def main():
    cfg = config.load()
    db_path = config.get_db_path(cfg)
    db = Database(db_path)
    manager = RecordManager(db, my_names=cfg.get("my_names", []))

    # LastReplay.rep 경로 탐색
    replay_path = config.get_last_replay_path(cfg)
    if not replay_path:
        print("[오류] LastReplay.rep 파일을 찾을 수 없습니다.")
        print("스타크래프트를 한 번 실행해 LastReplay.rep 파일을 생성해주세요.")
        print('또는 config.json에 "last_replay_path"를 직접 설정해주세요.')
        return

    print(f"감시 대상: {replay_path}")
    print(f"초기 파일 크기: {replay_path.stat().st_size:,} bytes")
    print(f"본인 닉네임: {manager.my_names or '(미설정)'}")
    print(f"1초 간격으로 감시 중... (Ctrl+C로 종료)")
    print("스타크래프트에서 게임을 시작하면 overlay가 표시됩니다.\n")

    callback = make_test_callback(manager, cfg)
    watcher = LastReplayWatcher(replay_path, callback)
    watcher.start()

    try:
        prev_size = replay_path.stat().st_size
        while True:
            time.sleep(2)
            try:
                cur_size = replay_path.stat().st_size
                if cur_size != prev_size:
                    diff = cur_size - prev_size
                    sign = "+" if diff > 0 else ""
                    print(f"  크기 변화: {prev_size:,} → {cur_size:,} ({sign}{diff:,} bytes)")
                    prev_size = cur_size
            except OSError:
                pass
    except KeyboardInterrupt:
        print("\n\n감시 종료.")
    finally:
        watcher.stop()


if __name__ == "__main__":
    main()
