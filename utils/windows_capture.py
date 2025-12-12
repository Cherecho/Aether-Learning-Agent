from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)


def _try_set_dpi_awareness() -> None:
    """Best-effort DPI awareness for correct window coordinates on Windows.

    If this fails, capture can still work but window rect math may be off when
    display scaling is enabled.
    """

    try:
        import ctypes

        # Per-monitor DPI awareness (Windows 8.1+)
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            return
        except Exception:
            pass

        # System DPI awareness (Vista+)
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    except Exception:
        pass


def is_windows() -> bool:
    import os

    return os.name == "nt"


def _require_windows() -> None:
    if not is_windows():
        raise OSError("windows_capture is only supported on Windows")


def _require_pywin32():
    try:
        import win32con  # noqa: F401
        import win32gui  # noqa: F401
        import win32process  # noqa: F401
    except Exception as exc:
        raise ImportError(
            "pywin32 is required for window-title capture. Install with: pip install pywin32"
        ) from exc


def list_visible_windows() -> list[tuple[int, str]]:
    """Return a list of (hwnd, title) for visible top-level windows."""

    _require_windows()
    _try_set_dpi_awareness()
    _require_pywin32()

    import win32gui

    results: list[tuple[int, str]] = []

    def enum_handler(hwnd: int, _lparam: int) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd) or ""
        title = title.strip()
        if not title:
            return
        results.append((hwnd, title))

    win32gui.EnumWindows(enum_handler, 0)
    return results


def find_window_hwnd(
    title_query: str,
    *,
    exact: bool = False,
    case_sensitive: bool = False,
) -> Optional[int]:
    """Find the first visible top-level window whose title matches query."""

    windows = list_visible_windows()

    def norm(s: str) -> str:
        return s if case_sensitive else s.lower()

    q = norm(title_query)
    for hwnd, title in windows:
        t = norm(title)
        if exact and t == q:
            return hwnd
        if not exact and q in t:
            return hwnd
    return None


def get_window_rect(hwnd: int, *, client_area: bool = True) -> Rect:
    """Get window rect in screen coordinates.

    If client_area is True, returns the drawable client rect (excludes borders/titlebar).
    """

    _require_windows()
    _try_set_dpi_awareness()
    _require_pywin32()

    import win32gui

    if client_area:
        left_top = win32gui.ClientToScreen(hwnd, (0, 0))
        client = win32gui.GetClientRect(hwnd)
        width = client[2] - client[0]
        height = client[3] - client[1]
        left, top = left_top
        return Rect(left=left, top=top, right=left + width, bottom=top + height)

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return Rect(left=left, top=top, right=right, bottom=bottom)


def capture_rect_bgra(rect: Rect):
    """Capture a screen rectangle. Returns an mss BGRA numpy array."""

    try:
        import mss
    except Exception as exc:
        raise ImportError("mss is required for capture. Install with: pip install mss") from exc

    with mss.mss() as sct:
        monitor = {
            "left": int(rect.left),
            "top": int(rect.top),
            "width": int(rect.width),
            "height": int(rect.height),
        }
        shot = sct.grab(monitor)

        import numpy as np

        # mss returns BGRA
        return np.asarray(shot)


def bgra_to_rgb(frame_bgra):
    import numpy as np

    if frame_bgra is None:
        raise ValueError("frame_bgra is None")

    # BGRA -> RGB
    b = frame_bgra[..., 0]
    g = frame_bgra[..., 1]
    r = frame_bgra[..., 2]
    return np.stack([r, g, b], axis=-1)


def capture_window_rgb(hwnd: int, *, client_area: bool = True):
    """Capture a specific window. Returns an RGB numpy array (H,W,3)."""

    rect = get_window_rect(hwnd, client_area=client_area)
    frame_bgra = capture_rect_bgra(rect)
    return bgra_to_rgb(frame_bgra)


def capture_fullscreen_rgb(monitor_index: int = 1):
    """Capture a whole monitor. Returns an RGB numpy array (H,W,3).

    monitor_index uses mss indexing: 1..N (0 is all monitors bounding box).
    """

    try:
        import mss
    except Exception as exc:
        raise ImportError("mss is required for capture. Install with: pip install mss") from exc

    with mss.mss() as sct:
        if monitor_index < 0 or monitor_index >= len(sct.monitors):
            raise ValueError(f"monitor_index must be in [0, {len(sct.monitors)-1}]")
        shot = sct.grab(sct.monitors[monitor_index])

        import numpy as np

        frame_bgra = np.asarray(shot)
        return bgra_to_rgb(frame_bgra)


def save_rgb_png(rgb, path: str) -> None:
    try:
        from PIL import Image
    except Exception as exc:
        raise ImportError("Pillow is required to save PNGs. Install with: pip install pillow") from exc

    img = Image.fromarray(rgb)
    img.save(path)
