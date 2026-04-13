"""설정 관리 모듈. config.json 파일을 통해 사용자 설정을 관리한다."""

import json
from pathlib import Path

CONFIG_DIR = Path(__file__).parent
DEFAULT_CONFIG_PATH = CONFIG_DIR / "config.json"
DEFAULT_DB_PATH = CONFIG_DIR / "star_record.db"

DEFAULTS = {
    "replay_dir": "",
    "starcraft_path": "",
    "db_path": str(DEFAULT_DB_PATH),
    "my_names": [],
    "auto_detect_me": True,
    "watch_interval_seconds": 2,
    "notify_on_new_game": True,
    "notify_mode": "toast",
    "last_replay_path": "",      # LastReplay.rep 절대 경로 (비어있으면 자동 탐색)
    "game_start_overlay": True,  # 게임 시작 시 overlay 표시 여부
}


def load(config_path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """설정 파일을 읽어서 딕셔너리로 반환한다. 없으면 기본값을 저장 후 반환."""
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
        # 누락된 키는 기본값으로 채운다
        merged = {**DEFAULTS, **user_config}
        return merged

    save(DEFAULTS, config_path)
    return dict(DEFAULTS)


def save(cfg: dict, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """딕셔너리를 config.json 파일로 저장한다."""
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def get_replay_dir(cfg: dict) -> Path | None:
    """설정에서 리플레이 디렉토리 경로를 반환한다. 비어있으면 None."""
    replay_dir = cfg.get("replay_dir", "")
    if not replay_dir:
        return None
    p = Path(replay_dir)
    return p if p.is_dir() else None


def get_db_path(cfg: dict) -> Path:
    """설정에서 DB 파일 경로를 반환한다."""
    return Path(cfg.get("db_path", str(DEFAULT_DB_PATH)))


def add_my_name(cfg: dict, name: str, config_path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """본인 닉네임을 추가하고 저장한다."""
    names = cfg.get("my_names", [])
    if name not in names:
        names.append(name)
        cfg["my_names"] = names
        save(cfg, config_path)
    return cfg


# LastReplay.rep 탐색 경로 (우선순위 순)
_LAST_REPLAY_CANDIDATES = [
    Path.home() / "Documents" / "StarCraft" / "Maps" / "Replays" / "LastReplay.rep",
    Path("C:/Users") / Path.home().name / "Documents" / "StarCraft" / "Maps" / "Replays" / "LastReplay.rep",
    Path("C:/Program Files (x86)/StarCraft/Maps/Replays/LastReplay.rep"),
]


def get_last_replay_path(cfg: dict) -> Path | None:
    """LastReplay.rep 경로를 반환한다. 설정에 있으면 그것을, 없으면 자동 탐색."""
    explicit = cfg.get("last_replay_path", "")
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p

    # replay_dir 기반 탐색
    replay_dir = cfg.get("replay_dir", "")
    if replay_dir:
        candidate = Path(replay_dir) / "LastReplay.rep"
        if candidate.exists():
            return candidate

    # 일반적인 경로 탐색
    for candidate in _LAST_REPLAY_CANDIDATES:
        if candidate.exists():
            return candidate

    return None
