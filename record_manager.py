"""전적 관리 모듈. 리플레이 파싱→DB 저장, 전적 조회, 본인 닉네임 추론을 담당한다."""

import re
import logging
from pathlib import Path
from datetime import datetime

from sc_replay_parser import SCReplayParser
from db import Database

log = logging.getLogger(__name__)

# 파일명에서 날짜를 추출하는 패턴: 2026-02-07@020624
DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})@(\d{6})")


class RecordManager:
    """리플레이 파싱, DB 저장, 전적 조회를 통합 관리한다."""

    def __init__(self, db: Database, my_names: list[str] | None = None):
        self.db = db
        self._my_names = set(my_names or [])

    @property
    def my_names(self) -> set[str]:
        """현재 등록된 본인 닉네임 집합."""
        db_names = set(self.db.get_my_names())
        return self._my_names | db_names

    # ── 리플레이 파싱 + DB 저장 ──────────────────────────────

    def process_replay(self, replay_path: Path) -> dict | None:
        """리플레이를 파싱하여 DB에 저장한다. 이미 저장된 파일이면 건너뛴다.
        Returns: 저장된 game_data dict, 또는 None (스킵/실패).
        """
        replay_file = replay_path.name

        if self.db.game_exists(replay_file):
            log.debug("이미 저장된 리플레이: %s", replay_file)
            return None

        try:
            parser = SCReplayParser(str(replay_path))
            parser.parse()
        except Exception as e:
            log.warning("리플레이 파싱 실패: %s - %s", replay_file, e)
            return None

        game_data = self._build_game_data(parser, replay_file)
        game_id = self.db.insert_game(game_data)

        self._save_players(game_id, parser)
        self._save_chat(game_id, parser)

        log.info("저장 완료: %s", replay_file)
        return game_data

    def import_folder(self, folder: Path) -> int:
        """폴더 내 모든 .rep 파일을 일괄 파싱하여 DB에 저장한다.
        Returns: 새로 저장된 게임 수.
        """
        rep_files = sorted(folder.glob("**/*.rep"))
        log.info("%d개의 리플레이 파일 발견", len(rep_files))

        count = 0
        for rep_file in rep_files:
            result = self.process_replay(rep_file)
            if result is not None:
                count += 1

        log.info("%d개 새로 저장됨", count)
        return count

    # ── 전적 조회 ────────────────────────────────────────────

    def get_record(self, opponent_name: str) -> dict:
        """특정 상대와의 전적을 조회한다."""
        return self.db.get_record_vs(opponent_name)

    def get_all_records(self) -> list[dict]:
        """모든 상대별 전적 요약을 조회한다."""
        return self.db.get_all_opponents()

    def format_record(self, record: dict) -> str:
        """전적 딕셔너리를 사람이 읽기 좋은 문자열로 변환한다."""
        if record["total"] == 0:
            return f"{record['opponent']}: 전적 없음"

        lines = [
            f"vs {record['opponent']}: "
            f"{record['wins']}승 {record['losses']}패 "
            f"(총 {record['total']}전)",
        ]

        for game in record["games"][:5]:  # 최근 5경기까지
            date = game.get("played_at", "?")[:10]
            map_name = game.get("map_name") or game.get("map_tileset") or "?"
            result = game.get("vs_result", "?")
            duration = game.get("duration_text", "")
            lines.append(f"  {date} | {result:4s} | {map_name} | {duration}")

        return "\n".join(lines)

    def format_record_short(self, record: dict) -> str:
        """알림용 짧은 전적 문자열."""
        if record["total"] == 0:
            return f"{record['opponent']}: 첫 대전"

        last_game = record["games"][0] if record["games"] else None
        last_date = ""
        if last_game and last_game.get("played_at"):
            last_date = f" (최근: {last_game['played_at'][:10]})"

        return (
            f"vs {record['opponent']}: "
            f"{record['wins']}승 {record['losses']}패{last_date}"
        )

    # ── 본인 닉네임 추론 ─────────────────────────────────────

    def detect_my_name(self) -> str | None:
        """DB에 저장된 게임들에서 가장 많이 등장하는 이름을 본인으로 추론한다.
        추론된 이름을 DB에 is_me=1로 표시하고 반환한다.
        """
        counts = self.db.get_player_name_counts()
        if not counts:
            return None

        # 이미 등록된 본인 이름이 있으면 그대로 유지
        existing = self.db.get_my_names()
        if existing:
            log.info("이미 등록된 본인 닉네임: %s", existing)
            return existing[0]

        # 가장 많이 등장하는 이름 = 본인
        best_name, best_count = counts[0]

        # 2위와 격차가 있어야 의미있는 추론
        if len(counts) >= 2:
            _, second_count = counts[1]
            if best_count <= second_count:
                log.warning("본인 닉네임 추론 불가: 상위 2명의 등장 횟수가 동일")
                return None

        self.db.set_player_is_me(best_name, True)
        self._my_names.add(best_name)
        log.info("본인 닉네임 추론: %s (%d회 등장)", best_name, best_count)
        return best_name

    # ── 내부 헬퍼 ────────────────────────────────────────────

    def _build_game_data(self, parser: SCReplayParser, replay_file: str) -> dict:
        """파서 결과에서 games 테이블용 딕셔너리를 구성한다."""
        gi = parser.game_info
        players = parser.players
        stats = parser.player_stats

        played_at = self._extract_datetime(replay_file)

        winner_name = gi.get("winner")
        loser_name = gi.get("loser")

        winner_race = None
        loser_race = None
        for p in players:
            if p["name"] == winner_name:
                winner_race = p["race"]
            elif p["name"] == loser_name:
                loser_race = p["race"]

        my_result = self._determine_my_result(winner_name, loser_name)

        return {
            "replay_file": replay_file,
            "played_at": played_at,
            "duration_seconds": gi.get("duration_seconds"),
            "duration_text": gi.get("duration") or gi.get("actual_duration"),
            "map_name": parser.map_data.get("map_name"),
            "map_tileset": parser.map_data.get("tileset"),
            "game_type": gi.get("game_type"),
            "winner_name": winner_name,
            "loser_name": loser_name,
            "winner_race": winner_race,
            "loser_race": loser_race,
            "my_result": my_result,
        }

    def _save_players(self, game_id: int, parser: SCReplayParser) -> None:
        """game_players 테이블에 플레이어 정보를 저장한다."""
        gi = parser.game_info
        for p in parser.players:
            player_id = self.db.get_or_create_player(p["name"])
            is_winner = p["name"] == gi.get("winner")
            apm = 0.0
            if p["id"] in parser.player_stats:
                apm = parser.player_stats[p["id"]].get("apm", 0.0)
            self.db.insert_game_player(game_id, player_id, p["race"], is_winner, apm)

    def _save_chat(self, game_id: int, parser: SCReplayParser) -> None:
        """chat_messages 테이블에 채팅을 저장한다."""
        for msg in parser.chat_messages:
            player_id = self.db.get_or_create_player(msg["player_name"])
            self.db.insert_chat_message(
                game_id, player_id,
                msg["message"], msg.get("time", ""), msg.get("frame", 0),
            )

    def _determine_my_result(self, winner_name: str | None,
                             loser_name: str | None) -> str:
        """승자/패자 이름과 본인 닉네임을 비교하여 my_result를 결정한다."""
        if not self.my_names:
            return "unknown"
        if winner_name in self.my_names:
            return "win"
        if loser_name in self.my_names:
            return "loss"
        return "unknown"

    @staticmethod
    def _extract_datetime(filename: str) -> str | None:
        """파일명에서 날짜시간을 추출한다.
        예: '2026-02-07@020624_...' → '2026-02-07 02:06:24'
        """
        match = DATE_PATTERN.search(filename)
        if not match:
            return None
        date_str, time_str = match.groups()
        time_formatted = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
        return f"{date_str} {time_formatted}"
