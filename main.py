"""star_record CLI 진입점.

사용법:
    python main.py import <리플레이_폴더>     기존 리플레이 일괄 가져오기
    python main.py watch <리플레이_폴더>      폴더 감시 + 자동 전적 알림
    python main.py launch                     스타크래프트와 함께 실행
    python main.py daemon                     백그라운드 프로세스 감시 모드
    python main.py record <상대닉네임>        특정 상대 전적 조회
    python main.py records                    전체 상대별 전적 요약
    python main.py set-name <닉네임>          본인 닉네임 수동 등록
    python main.py set-sc-path <경로>         스타크래프트 실행파일 경로 설정
    python main.py set-replay-dir <경로>      리플레이 폴더 경로 설정
    python main.py alias <원래이름> <별칭>    별칭 등록
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config
from db import Database
from record_manager import RecordManager
from notifier import show_toast

log = logging.getLogger("star_record")


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


# ── 콜백 팩토리 ─────────────────────────────────────────────

def make_replay_callback(manager: RecordManager, cfg: dict):
    """새 리플레이 감지 시 호출되는 콜백을 생성한다."""

    def on_new_replay(replay_path: Path):
        game_data = manager.process_replay(replay_path)
        if game_data is None:
            return

        my_names = manager.my_names
        winner = game_data.get("winner_name")
        loser = game_data.get("loser_name")

        if winner in my_names:
            opponent = loser
        elif loser in my_names:
            opponent = winner
        else:
            opponent = winner or loser

        if not opponent:
            return

        record = manager.get_record(opponent)
        short = manager.format_record_short(record)
        detail = manager.format_record(record)

        print(f"\n{detail}\n")

        if cfg.get("notify_on_new_game", True):
            show_toast("StarRecord - 전적 알림", short)

    return on_new_replay


# ── 명령어 핸들러 ────────────────────────────────────────────

def cmd_import(args, manager: RecordManager, cfg: dict):
    """기존 리플레이를 일괄 가져온다."""
    folder = Path(args.folder)
    if not folder.is_dir():
        log.error("폴더를 찾을 수 없습니다: %s", folder)
        return

    count = manager.import_folder(folder)
    print(f"\n{count}개의 리플레이를 가져왔습니다.")

    if cfg.get("auto_detect_me", True):
        detected = manager.detect_my_name()
        if detected:
            print(f"본인 닉네임 추론: {detected}")
            config.add_my_name(cfg, detected)


def cmd_watch(args, manager: RecordManager, cfg: dict):
    """리플레이 폴더를 감시하며 새 게임을 자동 처리한다."""
    try:
        from watcher import ReplayWatcher
    except ImportError:
        log.error("watchdog 패키지가 필요합니다: pip install watchdog")
        return

    folder = Path(args.folder)
    if not folder.is_dir():
        log.error("폴더를 찾을 수 없습니다: %s", folder)
        return

    cfg["replay_dir"] = str(folder)
    config.save(cfg)

    print(f"리플레이 폴더 감시 시작: {folder}")
    print("새 게임이 끝나면 자동으로 전적을 알려드립니다.")
    print("종료: Ctrl+C\n")

    callback = make_replay_callback(manager, cfg)
    watcher = ReplayWatcher(folder, callback)
    watcher.run_forever()


def cmd_launch(manager: RecordManager, cfg: dict):
    """스타크래프트와 리플레이 감시를 동시에 시작한다."""
    from launcher import launch_mode, find_starcraft_path

    # 스타크래프트 경로 확인
    sc_path_str = cfg.get("starcraft_path", "")
    if sc_path_str:
        sc_path = Path(sc_path_str)
    else:
        sc_path = find_starcraft_path()

    if not sc_path or not sc_path.exists():
        print("스타크래프트 경로를 찾을 수 없습니다.")
        print("다음 명령어로 경로를 설정해주세요:")
        print('  python main.py set-sc-path "C:/Program Files (x86)/StarCraft/StarCraft.exe"')
        return

    # 리플레이 폴더 확인
    replay_dir = _resolve_replay_dir(cfg)
    if not replay_dir:
        return

    callback = make_replay_callback(manager, cfg)
    launch_mode(sc_path, replay_dir, callback)


def cmd_daemon(manager: RecordManager, cfg: dict):
    """백그라운드에서 스타크래프트 프로세스를 감시한다."""
    from launcher import daemon_mode

    replay_dir = _resolve_replay_dir(cfg)
    if not replay_dir:
        return

    callback = make_replay_callback(manager, cfg)

    def on_sc_start():
        show_toast("StarRecord", "스타크래프트 감지! 리플레이 감시를 시작합니다.")

    def on_sc_stop():
        show_toast("StarRecord", "스타크래프트 종료. 리플레이 감시를 중지합니다.")

    daemon_mode(replay_dir, callback, on_sc_start, on_sc_stop)


def cmd_record(args, manager: RecordManager):
    """특정 상대와의 전적을 출력한다."""
    record = manager.get_record(args.opponent)
    print(manager.format_record(record))


def cmd_records(manager: RecordManager):
    """전체 상대별 전적 요약을 출력한다."""
    records = manager.get_all_records()
    if not records:
        print("저장된 전적이 없습니다.")
        return

    print(f"\n{'상대':20s} {'승':>4s} {'패':>4s} {'합계':>5s}  {'최근 대전':10s}")
    print("-" * 55)
    for r in records:
        last = (r["last_played"] or "")[:10]
        print(f"{r['opponent']:20s} {r['wins']:4d} {r['losses']:4d} {r['total']:5d}  {last}")
    print()


def cmd_set_name(args, manager: RecordManager, cfg: dict):
    """본인 닉네임을 수동 등록한다."""
    name = args.name
    manager.db.get_or_create_player(name)
    manager.db.set_player_is_me(name, True)
    config.add_my_name(cfg, name)
    print(f"본인 닉네임 등록: {name}")


def cmd_set_sc_path(args, cfg: dict):
    """스타크래프트 실행파일 경로를 설정한다."""
    sc_path = Path(args.path)
    if not sc_path.exists():
        print(f"경고: 파일이 존재하지 않습니다: {sc_path}")
        print("경로를 다시 확인해주세요.")
        return
    cfg["starcraft_path"] = str(sc_path)
    config.save(cfg)
    print(f"스타크래프트 경로 설정: {sc_path}")


def cmd_set_replay_dir(args, cfg: dict):
    """리플레이 폴더 경로를 설정한다."""
    replay_dir = Path(args.path)
    if not replay_dir.is_dir():
        print(f"경고: 폴더가 존재하지 않습니다: {replay_dir}")
        return
    cfg["replay_dir"] = str(replay_dir)
    config.save(cfg)
    print(f"리플레이 폴더 설정: {replay_dir}")


def cmd_alias(args, manager: RecordManager):
    """별칭을 등록한다."""
    manager.db.add_alias(args.player, args.alt)
    print(f"별칭 등록: {args.alt} → {args.player}")


# ── 헬퍼 ─────────────────────────────────────────────────────

def _resolve_replay_dir(cfg: dict) -> Path | None:
    """설정에서 리플레이 폴더를 가져오고, 없으면 안내 메시지를 출력한다."""
    replay_dir = config.get_replay_dir(cfg)
    if replay_dir:
        return replay_dir

    print("리플레이 폴더가 설정되지 않았습니다.")
    print("다음 명령어로 설정해주세요:")
    print('  python main.py set-replay-dir "C:/Users/.../Documents/StarCraft/Replays"')
    return None


# ── 메인 ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="StarRecord - 스타크래프트 전적 관리",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="상세 로그 출력")

    sub = parser.add_subparsers(dest="command")

    # import
    p_import = sub.add_parser("import", help="리플레이 일괄 가져오기")
    p_import.add_argument("folder", help="리플레이 폴더 경로")

    # watch
    p_watch = sub.add_parser("watch", help="리플레이 폴더 감시")
    p_watch.add_argument("folder", help="리플레이 폴더 경로")

    # launch
    sub.add_parser("launch", help="스타크래프트와 함께 실행")

    # daemon
    sub.add_parser("daemon", help="백그라운드 프로세스 감시 모드")

    # record
    p_record = sub.add_parser("record", help="상대 전적 조회")
    p_record.add_argument("opponent", help="상대 닉네임")

    # records
    sub.add_parser("records", help="전체 상대별 전적")

    # set-name
    p_name = sub.add_parser("set-name", help="본인 닉네임 등록")
    p_name.add_argument("name", help="닉네임")

    # set-sc-path
    p_sc = sub.add_parser("set-sc-path", help="스타크래프트 경로 설정")
    p_sc.add_argument("path", help="StarCraft.exe 경로")

    # set-replay-dir
    p_rd = sub.add_parser("set-replay-dir", help="리플레이 폴더 설정")
    p_rd.add_argument("path", help="리플레이 폴더 경로")

    # alias
    p_alias = sub.add_parser("alias", help="별칭 등록")
    p_alias.add_argument("player", help="원래 닉네임")
    p_alias.add_argument("alt", help="별칭")

    args = parser.parse_args()
    setup_logging(args.verbose)

    if not args.command:
        parser.print_help()
        return

    cfg = config.load()
    db = Database(config.get_db_path(cfg))
    manager = RecordManager(db, my_names=cfg.get("my_names", []))

    commands = {
        "import":         lambda: cmd_import(args, manager, cfg),
        "watch":          lambda: cmd_watch(args, manager, cfg),
        "launch":         lambda: cmd_launch(manager, cfg),
        "daemon":         lambda: cmd_daemon(manager, cfg),
        "record":         lambda: cmd_record(args, manager),
        "records":        lambda: cmd_records(manager),
        "set-name":       lambda: cmd_set_name(args, manager, cfg),
        "set-sc-path":    lambda: cmd_set_sc_path(args, cfg),
        "set-replay-dir": lambda: cmd_set_replay_dir(args, cfg),
        "alias":          lambda: cmd_alias(args, manager),
    }

    handler = commands.get(args.command)
    if handler:
        handler()


if __name__ == "__main__":
    main()
