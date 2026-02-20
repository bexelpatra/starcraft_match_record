"""SQLite 데이터베이스 모듈. 스키마 초기화와 CRUD 연산을 담당한다."""

import sqlite3
from pathlib import Path
from contextlib import contextmanager

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS players (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    is_me       INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS aliases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id   INTEGER NOT NULL,
    alt_name    TEXT UNIQUE NOT NULL,
    created_at  TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS games (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    replay_file      TEXT UNIQUE NOT NULL,
    played_at        TEXT,
    duration_seconds REAL,
    duration_text    TEXT,
    map_name         TEXT,
    map_tileset      TEXT,
    game_type        TEXT,
    winner_name      TEXT,
    loser_name       TEXT,
    winner_race      TEXT,
    loser_race       TEXT,
    my_result        TEXT,
    parsed_at        TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS game_players (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id   INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    race      TEXT,
    is_winner INTEGER DEFAULT 0,
    apm       REAL,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id   INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    message   TEXT,
    game_time TEXT,
    frame     INTEGER,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
);
"""


class Database:
    """SQLite 데이터베이스 래퍼. 스키마 초기화와 CRUD를 제공한다."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_schema()

    @contextmanager
    def _connect(self):
        """커넥션을 열고 자동 커밋/롤백하는 컨텍스트 매니저."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self):
        """테이블이 없으면 생성한다."""
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    # ── Players ──────────────────────────────────────────────

    def get_or_create_player(self, name: str) -> int:
        """플레이어를 이름으로 찾거나, 없으면 생성하여 id를 반환한다.
        alias 테이블도 함께 검색한다."""
        with self._connect() as conn:
            # 1) 정확한 이름 매칭
            row = conn.execute(
                "SELECT id FROM players WHERE name = ?", (name,)
            ).fetchone()
            if row:
                return row["id"]

            # 2) alias 검색
            row = conn.execute(
                "SELECT player_id FROM aliases WHERE alt_name = ?", (name,)
            ).fetchone()
            if row:
                return row["player_id"]

            # 3) 신규 생성
            cur = conn.execute(
                "INSERT INTO players (name) VALUES (?)", (name,)
            )
            return cur.lastrowid

    def set_player_is_me(self, name: str, is_me: bool = True) -> None:
        """특정 플레이어를 '본인'으로 표시한다."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE players SET is_me = ? WHERE name = ?",
                (int(is_me), name),
            )

    def get_my_names(self) -> list[str]:
        """is_me=1인 플레이어 이름 목록을 반환한다."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name FROM players WHERE is_me = 1"
            ).fetchall()
            return [r["name"] for r in rows]

    def add_alias(self, player_name: str, alt_name: str) -> None:
        """player_name에 대한 별칭(alt_name)을 등록한다."""
        player_id = self.get_or_create_player(player_name)
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO aliases (player_id, alt_name) VALUES (?, ?)",
                (player_id, alt_name),
            )

    def resolve_player_name(self, name: str) -> str:
        """alias라면 원래 이름으로 치환, 아니면 그대로 반환한다."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT p.name FROM aliases a JOIN players p ON a.player_id = p.id "
                "WHERE a.alt_name = ?",
                (name,),
            ).fetchone()
            return row["name"] if row else name

    # ── Games ────────────────────────────────────────────────

    def game_exists(self, replay_file: str) -> bool:
        """이미 파싱된 리플레이인지 확인한다."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM games WHERE replay_file = ?", (replay_file,)
            ).fetchone()
            return row is not None

    def insert_game(self, game_data: dict) -> int:
        """게임 레코드를 저장하고 id를 반환한다."""
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO games
                   (replay_file, played_at, duration_seconds, duration_text,
                    map_name, map_tileset, game_type,
                    winner_name, loser_name, winner_race, loser_race, my_result)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    game_data["replay_file"],
                    game_data.get("played_at"),
                    game_data.get("duration_seconds"),
                    game_data.get("duration_text"),
                    game_data.get("map_name"),
                    game_data.get("map_tileset"),
                    game_data.get("game_type"),
                    game_data.get("winner_name"),
                    game_data.get("loser_name"),
                    game_data.get("winner_race"),
                    game_data.get("loser_race"),
                    game_data.get("my_result"),
                ),
            )
            return cur.lastrowid

    def insert_game_player(self, game_id: int, player_id: int,
                           race: str, is_winner: bool, apm: float) -> None:
        """게임-플레이어 관계를 저장한다."""
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO game_players (game_id, player_id, race, is_winner, apm)
                   VALUES (?, ?, ?, ?, ?)""",
                (game_id, player_id, race, int(is_winner), apm),
            )

    def insert_chat_message(self, game_id: int, player_id: int,
                            message: str, game_time: str, frame: int) -> None:
        """채팅 메시지를 저장한다."""
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO chat_messages (game_id, player_id, message, game_time, frame)
                   VALUES (?, ?, ?, ?, ?)""",
                (game_id, player_id, message, game_time, frame),
            )

    # ── 전적 조회 ────────────────────────────────────────────

    def get_record_vs(self, opponent_name: str) -> dict:
        """특정 상대와의 전적을 반환한다.
        Returns: {wins, losses, total, games: [{played_at, map, result, duration, ...}]}
        """
        # alias 해소
        resolved = self.resolve_player_name(opponent_name)

        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM games
                   WHERE winner_name = ? OR loser_name = ?
                   ORDER BY played_at DESC""",
                (resolved, resolved),
            ).fetchall()

        my_names = set(self.get_my_names())
        wins = 0
        losses = 0
        games = []

        for row in rows:
            game = dict(row)
            # 내가 이긴 경우
            if game["winner_name"] in my_names and game["loser_name"] == resolved:
                wins += 1
                game["vs_result"] = "win"
            elif game["loser_name"] in my_names and game["winner_name"] == resolved:
                losses += 1
                game["vs_result"] = "loss"
            else:
                game["vs_result"] = "unknown"
            games.append(game)

        return {
            "opponent": resolved,
            "wins": wins,
            "losses": losses,
            "total": wins + losses,
            "games": games,
        }

    def get_all_opponents(self) -> list[dict]:
        """모든 상대별 전적 요약을 반환한다."""
        my_names = set(self.get_my_names())
        if not my_names:
            return []

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM games ORDER BY played_at DESC"
            ).fetchall()

        stats = {}
        for row in rows:
            game = dict(row)
            winner = game["winner_name"]
            loser = game["loser_name"]

            if winner in my_names and loser and loser not in my_names:
                opponent = loser
                result = "win"
            elif loser in my_names and winner and winner not in my_names:
                opponent = winner
                result = "loss"
            else:
                continue

            if opponent not in stats:
                stats[opponent] = {"wins": 0, "losses": 0, "last_played": None}

            if result == "win":
                stats[opponent]["wins"] += 1
            else:
                stats[opponent]["losses"] += 1

            if stats[opponent]["last_played"] is None:
                stats[opponent]["last_played"] = game["played_at"]

        result_list = []
        for name, s in sorted(stats.items()):
            result_list.append({
                "opponent": name,
                "wins": s["wins"],
                "losses": s["losses"],
                "total": s["wins"] + s["losses"],
                "last_played": s["last_played"],
            })
        return result_list

    def get_player_name_counts(self) -> list[tuple[str, int]]:
        """모든 게임에서 등장한 플레이어 이름별 등장 횟수를 반환한다.
        본인 닉네임 자동 추론에 사용된다."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT name, count FROM (
                     SELECT winner_name AS name, COUNT(*) AS count FROM games
                     WHERE winner_name IS NOT NULL GROUP BY winner_name
                     UNION ALL
                     SELECT loser_name AS name, COUNT(*) AS count FROM games
                     WHERE loser_name IS NOT NULL GROUP BY loser_name
                   ) ORDER BY count DESC"""
            ).fetchall()
        return [(r["name"], r["count"]) for r in rows]
