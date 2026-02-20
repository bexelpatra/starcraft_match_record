"""Windows 토스트 알림 모듈. 전적 정보를 알림으로 표시한다."""

import logging
import subprocess
import sys

log = logging.getLogger(__name__)


def show_toast(title: str, message: str, duration: int = 10) -> None:
    """Windows 토스트 알림을 표시한다.

    PowerShell의 BurntToast 없이 기본 Windows API를 사용한다.
    plyer가 설치되어 있으면 우선 사용하고, 없으면 PowerShell 폴백.

    Args:
        title: 알림 제목
        message: 알림 본문
        duration: 표시 시간 (초)
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
        # 최후 수단: 콘솔 출력
        print(f"\n{'='*50}")
        print(f"  {title}")
        print(f"  {message}")
        print(f"{'='*50}\n")


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
    """PowerShell을 이용한 Windows 토스트 알림 (외부 모듈 불필요)."""
    # XML 특수문자 이스케이프
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
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("StarRecord").Show($toast)
    """

    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True,
        timeout=10,
    )
    log.debug("PowerShell 알림 표시 완료")


def _escape_xml(text: str) -> str:
    """XML 특수문자를 이스케이프한다."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
