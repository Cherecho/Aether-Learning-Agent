from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _ensure_repo_root_on_syspath() -> None:
    """Allow running this file directly: `python .\\tools\\capture_screen.py ...`.

    When executed as a script, Python puts the script folder (tools/) on sys.path,
    not the repo root. Our imports live at the repo root (utils/), so we add the
    parent directory.
    """

    repo_root = Path(__file__).resolve().parent.parent
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)


_ensure_repo_root_on_syspath()


from utils.windows_capture import (
    capture_fullscreen_rgb,
    capture_window_rgb,
    find_window_hwnd,
    list_visible_windows,
    save_rgb_png,
)


def _resolve_unique_path(path: Path) -> Path:
    """If path exists, append an incrementing suffix before the extension."""

    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    idx = 1
    while True:
        candidate = parent / f"{stem}{idx}{suffix}"
        if not candidate.exists():
            return candidate
        idx += 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Capture frames from Clash Royale (or any) window / full screen on Windows."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List visible windows (hwnd + title)")
    p_list.add_argument("--contains", default="", help="Optional substring filter")

    p_cap = sub.add_parser("capture", help="Capture to a PNG")
    src = p_cap.add_mutually_exclusive_group(required=True)
    src.add_argument("--window-title", help="Capture first window containing this title")
    src.add_argument("--monitor", type=int, help="Capture entire monitor (mss index: 1..N)")
    p_cap.add_argument("--exact", action="store_true", help="Exact match for window title")
    p_cap.add_argument(
        "--include-borders",
        action="store_true",
        help="Capture full window including borders/titlebar (default: client area only)",
    )
    p_cap.add_argument(
        "--out",
        type=Path,
        default=Path("capture.png"),
        help="Output PNG path",
    )

    args = parser.parse_args(argv)

    if args.cmd == "list":
        items = list_visible_windows()
        q = (args.contains or "").lower().strip()
        for hwnd, title in items:
            if q and q not in title.lower():
                continue
            print(f"{hwnd}\t{title}")
        return 0

    if args.cmd == "capture":
        out_path: Path = _resolve_unique_path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if args.window_title:
            hwnd = find_window_hwnd(args.window_title, exact=args.exact)
            if hwnd is None:
                print(
                    f"Could not find a visible window matching: {args.window_title!r}",
                    file=sys.stderr,
                )
                return 2
            rgb = capture_window_rgb(hwnd, client_area=not args.include_borders)
            save_rgb_png(rgb, str(out_path))
            print(f"Saved {out_path} from hwnd={hwnd}")
            return 0

        if args.monitor is not None:
            rgb = capture_fullscreen_rgb(args.monitor)
            save_rgb_png(rgb, str(out_path))
            print(f"Saved {out_path} from monitor={args.monitor}")
            return 0

        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
