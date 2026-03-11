"""Windows 알림 모듈. 토스트 알림과 오버레이 팝업을 제공한다."""

import logging
import os
import subprocess
import sys
import tempfile
import threading

log = logging.getLogger(__name__)


# ── 통합 API ──────────────────────────────────────────────────

def notify(title: str, message: str, opponents: list[dict] | None = None,
           cfg: dict | None = None) -> None:
    """통합 알림 함수. cfg['notify_mode']에 따라 방식을 선택한다.

    Args:
        title: 알림 제목
        message: 알림 본문 (toast용)
        opponents: 상대 정보 리스트 (overlay용).
                   각 dict에 name, race, record 키를 포함.
        cfg: 설정 딕셔너리. notify_mode 키로 방식 선택.
             "toast" | "overlay" | "both" (기본값: "toast")
    """
    mode = (cfg or {}).get("notify_mode", "toast")
    if mode in ("toast", "both"):
        show_toast(title, message)
    if mode in ("overlay", "both") and opponents:
        show_overlay(title, opponents)


# ── Toast 알림 ────────────────────────────────────────────────

def show_toast(title: str, message: str, duration: int = 10) -> None:
    """Windows 토스트 알림을 표시한다.

    plyer → PowerShell (.ps1) → 콘솔 순으로 폴백한다.
    """
    try:
        _show_with_plyer(title, message, duration)
        return
    except ImportError:
        pass
    except Exception as e:
        log.debug("plyer 알림 실패, PowerShell 폴백: %s", e)

    try:
        _show_with_powershell(title, message, duration)
    except Exception as e:
        log.warning("알림 표시 실패: %s", e)
        _show_with_console(title, message)


# ── Overlay 팝업 ──────────────────────────────────────────────

def show_overlay(title: str, opponents: list[dict], duration: int = 5) -> None:
    """tkinter 오버레이 팝업을 별도 스레드에서 표시한다.

    Args:
        title: 팝업 제목
        opponents: 상대 정보 리스트. 각 dict에 name, race, record 키.
        duration: 표시 시간 (초)
    """
    t = threading.Thread(
        target=_show_with_overlay,
        args=(title, opponents, duration),
        daemon=True,
    )
    t.start()


# ── 내부 구현 ─────────────────────────────────────────────────

def _show_with_plyer(title: str, message: str, duration: int) -> None:
    """plyer 라이브러리로 알림을 표시한다."""
    from plyer import notification
    notification.notify(
        title=title,
        message=message,
        timeout=duration,
        app_name="StarRecord",
    )
    log.debug("plyer 알림 표시 완료")


def _show_with_powershell(title: str, message: str, duration: int) -> None:
    """PowerShell을 이용한 Windows 토스트 알림.

    $ 변수 소실 방지를 위해 임시 .ps1 파일을 생성하여 실행한다.
    """
    safe_title = _escape_xml(title)
    safe_message = _escape_xml(message)

    ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null

$template = @"
<toast duration="long">
    <visual>
        <binding template="ToastGeneric">
            <text>{safe_title}</text>
            <text>{safe_message}</text>
        </binding>
    </visual>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
$appId = "{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\\WindowsPowerShell\\v1.0\\powershell.exe"
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
"""

    # 임시 .ps1 파일에 쓰고 실행
    fd, ps_path = tempfile.mkstemp(suffix=".ps1", prefix="star_record_toast_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(ps_script)
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", ps_path],
            capture_output=True,
            timeout=10,
        )
        log.debug("PowerShell 알림 표시 완료")
    finally:
        try:
            os.unlink(ps_path)
        except OSError:
            pass


def _show_with_overlay(title: str, opponents: list[dict], duration: int) -> None:
    """tkinter 오버레이 팝업을 표시한다. 별도 스레드에서 호출된다."""
    try:
        import tkinter as tk
    except ImportError:
        log.warning("tkinter를 사용할 수 없어 오버레이를 표시할 수 없습니다.")
        return

    root = tk.Tk()
    root.title("StarRecord")

    # 항상 최상위 + 테두리 없음 + 반투명
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.85)
    root.overrideredirect(True)

    # 상대 수에 따라 높이 동적 조절
    base_height = 60  # 제목 + 구분선 영역
    row_height = 20
    height = base_height + row_height * max(len(opponents), 1) + 15
    width = 320

    # 화면 오른쪽 상단에 배치
    screen_w = root.winfo_screenwidth()
    x = screen_w - width - 20
    y = 20
    root.geometry(f"{width}x{height}+{x}+{y}")

    bg_color = "#1a1a2e"
    accent_color = "#e94560"
    text_color = "#ffffff"
    record_color = "#00d2d3"

    root.configure(bg=bg_color)

    # 제목
    tk.Label(
        root, text=title, font=("Consolas", 14, "bold"),
        fg=accent_color, bg=bg_color,
    ).pack(pady=(10, 5))

    # 구분선
    tk.Frame(root, height=1, bg=accent_color).pack(fill="x", padx=15)

    # 상대 전적 행
    for opp in opponents:
        name = opp.get("name", "?")
        race = opp.get("race", "?")
        record = opp.get("record", "")

        row = tk.Frame(root, bg=bg_color)
        row.pack(fill="x", padx=15, pady=1)
        tk.Label(
            row, text=f"{name} ({race})", font=("Consolas", 9),
            fg=text_color, bg=bg_color, anchor="w",
        ).pack(side="left")
        tk.Label(
            row, text=record, font=("Consolas", 9),
            fg=record_color, bg=bg_color, anchor="e",
        ).pack(side="right")

    # duration 초 후 자동 닫힘
    root.after(duration * 1000, root.destroy)
    root.mainloop()


def _show_with_console(title: str, message: str) -> None:
    """최후 수단: 콘솔 출력."""
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"  {message}")
    print(f"{'='*50}\n")


def _escape_xml(text: str) -> str:
    """XML 특수문자를 이스케이프한다."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
