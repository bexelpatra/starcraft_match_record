"""StarRecord GUI 설정 화면. tkinter 기반 설정/관리 인터페이스."""

import tkinter as tk
import threading
from tkinter import filedialog
from pathlib import Path

import config
from db import Database
from record_manager import RecordManager
from notifier import notify

# 테마 색상
BG = "#1a1a2e"
FRAME_BG = "#16213e"
FG = "#ffffff"
BTN_BG = "#0f3460"
BTN_ACTIVE = "#e94560"
ENTRY_BG = "#16213e"
ENTRY_FG = "#ffffff"


class StarRecordGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.cfg = config.load()

        # DB와 RecordManager 초기화
        db = Database(config.get_db_path(self.cfg))
        self.manager = RecordManager(db, my_names=self.cfg.get("my_names", []))

        self._running = False  # 실행 중 여부
        self._last_replay_watcher = None  # LastReplayWatcher 인스턴스
        self._build_ui()

    def run(self):
        self.root.mainloop()

    # ── UI 구성 ──────────────────────────────────────────

    def _build_ui(self):
        root = self.root
        root.title("StarRecord")
        root.configure(bg=BG)
        root.minsize(500, 520)
        root.resizable(False, False)

        # LabelFrame 공통 스타일
        lf_opts = dict(bg=FRAME_BG, fg=FG, font=("맑은 고딕", 10, "bold"), padx=8, pady=6)

        # ── 기본 설정 ────────────────────────────────────
        frm_basic = tk.LabelFrame(root, text="기본 설정", **lf_opts)
        frm_basic.pack(fill="x", padx=10, pady=(10, 4))

        # 닉네임
        tk.Label(frm_basic, text="닉네임:", bg=FRAME_BG, fg=FG).grid(row=0, column=0, sticky="w", pady=3)
        self.name_var = tk.StringVar(value=self.cfg["my_names"][0] if self.cfg.get("my_names") else "")
        ent_name = tk.Entry(frm_basic, textvariable=self.name_var, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG, width=30)
        ent_name.grid(row=0, column=1, padx=4, pady=3)
        tk.Button(frm_basic, text="저장", command=self._save_name, bg=BTN_BG, fg=FG, activebackground=BTN_ACTIVE, activeforeground=FG, relief="flat", width=6).grid(row=0, column=2, padx=4, pady=3)

        # 리플레이 폴더
        tk.Label(frm_basic, text="리플레이 폴더:", bg=FRAME_BG, fg=FG).grid(row=1, column=0, sticky="w", pady=3)
        self.replay_var = tk.StringVar(value=self.cfg.get("replay_dir", ""))
        ent_replay = tk.Entry(frm_basic, textvariable=self.replay_var, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG, width=30, state="readonly", readonlybackground=ENTRY_BG)
        ent_replay.grid(row=1, column=1, padx=4, pady=3)
        tk.Button(frm_basic, text="찾기", command=self._browse_replay_dir, bg=BTN_BG, fg=FG, activebackground=BTN_ACTIVE, activeforeground=FG, relief="flat", width=6).grid(row=1, column=2, padx=4, pady=3)

        # SC 경로
        tk.Label(frm_basic, text="SC 경로:", bg=FRAME_BG, fg=FG).grid(row=2, column=0, sticky="w", pady=3)
        self.sc_var = tk.StringVar(value=self.cfg.get("starcraft_path", ""))
        ent_sc = tk.Entry(frm_basic, textvariable=self.sc_var, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG, width=30, state="readonly", readonlybackground=ENTRY_BG)
        ent_sc.grid(row=2, column=1, padx=4, pady=3)
        tk.Button(frm_basic, text="찾기", command=self._browse_sc_path, bg=BTN_BG, fg=FG, activebackground=BTN_ACTIVE, activeforeground=FG, relief="flat", width=6).grid(row=2, column=2, padx=4, pady=3)

        frm_basic.columnconfigure(1, weight=1)

        # ── 알림 설정 ────────────────────────────────────
        frm_notify = tk.LabelFrame(root, text="알림 설정", **lf_opts)
        frm_notify.pack(fill="x", padx=10, pady=4)

        tk.Label(frm_notify, text="알림 방식:", bg=FRAME_BG, fg=FG).pack(side="left", padx=(0, 8))
        self.notify_var = tk.StringVar(value=self.cfg.get("notify_mode", "toast"))
        for text, val in [("Toast", "toast"), ("Overlay", "overlay"), ("Both", "both")]:
            tk.Radiobutton(
                frm_notify, text=text, variable=self.notify_var, value=val,
                command=self._save_notify_mode,
                bg=FRAME_BG, fg=FG, selectcolor=BG, activebackground=FRAME_BG, activeforeground=FG,
            ).pack(side="left", padx=6)

        # ── 실행 ─────────────────────────────────────────
        frm_run = tk.LabelFrame(root, text="실행", **lf_opts)
        frm_run.pack(fill="x", padx=10, pady=4)

        btn_style = dict(bg=BTN_BG, fg=FG, activebackground=BTN_ACTIVE, activeforeground=FG, relief="flat", width=20, height=2)
        self.btn_launch = tk.Button(frm_run, text="게임 시작 (Launch)", command=self._on_launch, **btn_style)
        self.btn_launch.pack(side="left", padx=8, pady=6)
        self.btn_daemon = tk.Button(frm_run, text="데몬 모드 (Daemon)", command=self._on_daemon, **btn_style)
        self.btn_daemon.pack(side="left", padx=8, pady=6)
        self.btn_stop = tk.Button(frm_run, text="중지", command=self._on_stop, bg="#e94560", fg=FG, activebackground="#c0392b", activeforeground=FG, relief="flat", width=8, height=2, state="disabled")
        self.btn_stop.pack(side="left", padx=8, pady=6)

        # ── 전적 ─────────────────────────────────────────
        frm_record = tk.LabelFrame(root, text="전적", **lf_opts)
        frm_record.pack(fill="x", padx=10, pady=4)

        tk.Button(frm_record, text="전적 보기", command=self._on_view_records, **btn_style).pack(side="left", padx=8, pady=6)
        tk.Button(frm_record, text="리플레이 가져오기", command=self._on_import_replays, **btn_style).pack(side="left", padx=8, pady=6)

        # ── 상태바 ───────────────────────────────────────
        self.status_var = tk.StringVar(value="대기 중")
        status_bar = tk.Label(root, textvariable=self.status_var, bg=BG, fg=FG, anchor="w", padx=10, pady=4)
        status_bar.pack(fill="x", side="bottom")

    # ── 콜백: 기본 설정 ──────────────────────────────────

    def _save_name(self):
        name = self.name_var.get().strip()
        if not name:
            return
        config.add_my_name(self.cfg, name)
        self.status_var.set(f"닉네임 '{name}' 저장됨")

    def _browse_replay_dir(self):
        path = filedialog.askdirectory(title="리플레이 폴더 선택")
        if path:
            self.replay_var.set(path)
            self.cfg["replay_dir"] = path
            config.save(self.cfg)
            self.status_var.set(f"리플레이 폴더 설정: {path}")

    def _browse_sc_path(self):
        path = filedialog.askopenfilename(title="StarCraft 실행 파일 선택", filetypes=[("실행 파일", "*.exe"), ("모든 파일", "*.*")])
        if path:
            self.sc_var.set(path)
            self.cfg["starcraft_path"] = path
            config.save(self.cfg)
            self.status_var.set(f"SC 경로 설정: {path}")

    # ── 콜백: 알림 설정 ──────────────────────────────────

    def _save_notify_mode(self):
        value = self.notify_var.get()
        self.cfg["notify_mode"] = value
        config.save(self.cfg)
        self.status_var.set(f"알림 방식: {value}")

    # ── 콜백: 실행 ────────────────────────────────────────

    def _on_launch(self):
        """스타크래프트와 리플레이 감시를 동시에 시작한다."""
        if self._running:
            return

        from launcher import find_starcraft_path

        sc_path_str = self.cfg.get("starcraft_path", "")
        sc_path = Path(sc_path_str) if sc_path_str else find_starcraft_path()

        if not sc_path or not sc_path.exists():
            self._set_status("SC 경로를 설정해주세요")
            return

        replay_dir = config.get_replay_dir(self.cfg)
        if not replay_dir:
            self._set_status("리플레이 폴더를 설정해주세요")
            return

        self._running = True
        self._set_status("스타크래프트 실행 중...")
        self.btn_launch.config(state="disabled")
        self.btn_daemon.config(state="disabled")
        self.btn_stop.config(state="normal")

        def run():
            from launcher import launch_mode
            callback = self._make_callback()
            try:
                launch_mode(sc_path, replay_dir, callback)
            finally:
                self._running = False
                self.root.after(0, self._restore_buttons)

        threading.Thread(target=run, daemon=True).start()

    def _on_daemon(self):
        """데몬 모드로 SC 프로세스를 감시한다."""
        if self._running:
            return

        replay_dir = config.get_replay_dir(self.cfg)
        if not replay_dir:
            self._set_status("리플레이 폴더를 설정해주세요")
            return

        self._running = True
        self._set_status("데몬 모드 실행 중 — SC 프로세스 감시 중")
        self.btn_launch.config(state="disabled")
        self.btn_daemon.config(state="disabled")
        self.btn_stop.config(state="normal")

        def run():
            from launcher import daemon_mode
            from watcher import LastReplayWatcher

            callback = self._make_callback()

            # LastReplay.rep 감시 (게임 시작 감지)
            last_replay_path = config.get_last_replay_path(self.cfg)
            if last_replay_path:
                game_start_cb = self._make_game_start_callback()
                self._last_replay_watcher = LastReplayWatcher(last_replay_path, game_start_cb)
                self._last_replay_watcher.start()
                self.root.after(0, lambda: self._set_status("데몬 + 게임 시작 감지 실행 중"))

            def on_sc_start():
                self.root.after(0, lambda: self._set_status("SC 감지! 리플레이 감시 중"))

            def on_sc_stop():
                self.root.after(0, lambda: self._set_status("SC 종료. 다시 감시 중..."))

            try:
                daemon_mode(replay_dir, callback, on_sc_start, on_sc_stop)
            finally:
                if self._last_replay_watcher:
                    self._last_replay_watcher.stop()
                    self._last_replay_watcher = None
                self._running = False
                self.root.after(0, self._restore_buttons)

        threading.Thread(target=run, daemon=True).start()

    def _on_stop(self):
        """실행 중인 감시를 중지한다."""
        if not self._running:
            return
        if self._last_replay_watcher:
            self._last_replay_watcher.stop()
            self._last_replay_watcher = None
        self._running = False
        self._restore_buttons()
        self._set_status("중지됨")

    def _restore_buttons(self):
        """버튼 상태를 초기화한다."""
        self.btn_launch.config(state="normal")
        self.btn_daemon.config(state="normal")
        self.btn_stop.config(state="disabled")
        self._set_status("대기 중")

    # ── 콜백 헬퍼 ───────────────────────────────────────

    def _make_callback(self):
        """새 리플레이 감지 시 호출되는 콜백."""
        manager = self.manager
        cfg = self.cfg

        def on_new_replay(replay_path):
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

            # 메모 조회
            latest_memo = manager.db.get_latest_memo(opponent)

            opp_race = game_data.get("loser_race") if winner in my_names \
                else game_data.get("winner_race")
            opponents = [{
                "name": opponent,
                "race": opp_race or "?",
                "record": f"{record['wins']}승 {record['losses']}패",
                "memo": latest_memo,
            }]

            if cfg.get("notify_on_new_game", True):
                notify("StarRecord - 전적 알림", short, opponents=opponents, cfg=cfg)

            self.root.after(0, lambda: self._set_status(f"새 게임: vs {opponent} — {short}"))

        return on_new_replay

    def _make_game_start_callback(self):
        """게임 시작(LastReplay.rep 변화) 시 호출되는 콜백."""
        from sc_replay_parser import SCReplayParser
        manager = self.manager
        cfg = self.cfg

        def on_game_start(replay_path):
            if not cfg.get("game_start_overlay", True):
                return
            try:
                parser = SCReplayParser(str(replay_path))
                parser.parse_header_only()
            except Exception:
                return

            players = parser.players
            if not players:
                return

            my_names = manager.my_names
            opponents_info = []
            for p in players:
                if p["name"] not in my_names:
                    record = manager.get_record(p["name"])
                    wins = record.get("wins", 0)
                    losses = record.get("losses", 0)
                    total = record.get("total", 0)
                    record_str = "첫 대전" if total == 0 else f"{wins}승 {losses}패"
                    latest_memo = manager.db.get_latest_memo(p["name"])
                    opponents_info.append({
                        "name": p["name"],
                        "race": p.get("race", "?"),
                        "record": record_str,
                        "memo": latest_memo,
                    })

            if not opponents_info:
                for p in players:
                    record = manager.get_record(p["name"])
                    wins = record.get("wins", 0)
                    losses = record.get("losses", 0)
                    total = record.get("total", 0)
                    record_str = "첫 대전" if total == 0 else f"{wins}승 {losses}패"
                    latest_memo = manager.db.get_latest_memo(p["name"])
                    opponents_info.append({
                        "name": p["name"],
                        "race": p.get("race", "?"),
                        "record": record_str,
                        "memo": latest_memo,
                    })

            if opponents_info:
                notify("StarRecord - 게임 시작", "",
                       opponents=opponents_info, cfg={**cfg, "notify_mode": "overlay"})
                names = ", ".join(o["name"] for o in opponents_info)
                self.root.after(0, lambda: self._set_status(f"게임 시작: vs {names}"))

        return on_game_start

    # ── 콜백: 전적 ──────────────────────────────────────

    def _on_view_records(self):
        """전체 상대별 전적을 새 창에 표시한다."""
        records = self.manager.get_all_records()

        win = tk.Toplevel(self.root)
        win.title("전적 보기")
        win.geometry("450x400")
        win.configure(bg="#1a1a2e")

        if not records:
            tk.Label(win, text="저장된 전적이 없습니다.", fg="#ffffff", bg="#1a1a2e",
                     font=("Consolas", 11)).pack(pady=20)
            return

        # 헤더
        header = tk.Frame(win, bg="#16213e")
        header.pack(fill="x", padx=10, pady=(10, 0))
        for col, w in [("상대", 18), ("승", 5), ("패", 5), ("합계", 5), ("최근", 10)]:
            tk.Label(header, text=col, width=w, anchor="w", fg="#e94560", bg="#16213e",
                     font=("Consolas", 9, "bold")).pack(side="left")

        # 스크롤 가능한 리스트
        container = tk.Frame(win, bg="#1a1a2e")
        container.pack(fill="both", expand=True, padx=10, pady=5)

        for r in records:
            row = tk.Frame(container, bg="#1a1a2e")
            row.pack(fill="x")
            last = (r["last_played"] or "")[:10]
            for val, w in [(r["opponent"], 18), (str(r["wins"]), 5), (str(r["losses"]), 5),
                           (str(r["total"]), 5), (last, 10)]:
                tk.Label(row, text=val, width=w, anchor="w", fg="#ffffff", bg="#1a1a2e",
                         font=("Consolas", 9)).pack(side="left")

    def _on_import_replays(self):
        """폴더를 선택하여 리플레이를 일괄 가져온다."""
        folder = filedialog.askdirectory(title="리플레이 폴더 선택")
        if not folder:
            return

        self._set_status(f"가져오는 중: {folder}")

        def run():
            count = self.manager.import_folder(Path(folder))

            if self.cfg.get("auto_detect_me", True):
                detected = self.manager.detect_my_name()
                if detected:
                    config.add_my_name(self.cfg, detected)

            self.root.after(0, lambda: self._set_status(f"{count}개 리플레이 가져옴"))

        threading.Thread(target=run, daemon=True).start()

    # ── 상태 헬퍼 ───────────────────────────────────────

    def _set_status(self, text: str):
        """상태바 텍스트를 업데이트한다."""
        self.status_var.set(text)


if __name__ == "__main__":
    app = StarRecordGUI()
    app.run()
