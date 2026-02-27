"""오버레이 팝업 테스트 - 게임 위에 표시되는지 확인용"""
import tkinter as tk


def show_overlay():
    root = tk.Tk()
    root.title("StarRecord")

    # 항상 최상위 + 테두리 없음 + 반투명
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.85)
    root.overrideredirect(True)  # 타이틀바 제거

    # 화면 오른쪽 상단에 배치
    width, height = 320, 220
    screen_w = root.winfo_screenwidth()
    x = screen_w - width - 20
    y = 20
    root.geometry(f"{width}x{height}+{x}+{y}")

    # 배경색
    root.configure(bg="#1a1a2e")

    # 제목
    tk.Label(
        root, text="Star Record", font=("Consolas", 14, "bold"),
        fg="#e94560", bg="#1a1a2e"
    ).pack(pady=(10, 5))

    # 구분선
    tk.Frame(root, height=1, bg="#e94560").pack(fill="x", padx=15)

    # 상대 전적 예시 (7명)
    opponents = [
        ("MiniMaxii", "P", "3승 1패"),
        ("HM_sSak", "T", "1승 2패"),
        ("YB_Scan", "Z", "0승 3패"),
        ("Player4", "T", "5승 0패"),
        ("Player5", "P", "2승 2패"),
        ("Player6", "Z", "1승 1패"),
        ("Player7", "T", "첫 상대"),
    ]

    for name, race, record in opponents:
        row = tk.Frame(root, bg="#1a1a2e")
        row.pack(fill="x", padx=15, pady=1)
        tk.Label(
            row, text=f"{name} ({race})", font=("Consolas", 9),
            fg="#ffffff", bg="#1a1a2e", anchor="w"
        ).pack(side="left")
        tk.Label(
            row, text=record, font=("Consolas", 9),
            fg="#00d2d3", bg="#1a1a2e", anchor="e"
        ).pack(side="right")

    # 5초 후 자동 닫힘
    root.after(5000, root.destroy)
    root.mainloop()


if __name__ == "__main__":
    show_overlay()
