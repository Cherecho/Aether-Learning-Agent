from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def _ensure_repo_root_on_syspath() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)


_ensure_repo_root_on_syspath()

from utils.windows_capture import find_window_hwnd, get_window_rect
from utils.windows_input import click_at, drag, move_mouse


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Test input simulation.")
    parser.add_argument(
        "--window-title",
        default="Clash Royale",
        help="Target window title (default: Clash Royale)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Click center
    sub.add_parser("click-center", help="Click the center of the window")

    # Drag test
    p_drag = sub.add_parser("drag-test", help="Simulate a drag operation")
    p_drag.add_argument("--dx", type=int, default=100, help="Delta X for drag")
    p_drag.add_argument("--dy", type=int, default=0, help="Delta Y for drag")

    args = parser.parse_args(argv)

    hwnd = find_window_hwnd(args.window_title)
    if not hwnd:
        print(f"Window '{args.window_title}' not found.")
        return 1

    rect = get_window_rect(hwnd, client_area=True)
    print(f"Found window at: {rect}")

    # Calculate center
    center_x = int(rect.left + rect.width / 2)
    center_y = int(rect.top + rect.height / 2)

    if args.cmd == "click-center":
        print(f"Clicking at ({center_x}, {center_y}) in 2 seconds...")
        time.sleep(2)
        click_at(center_x, center_y)
        print("Clicked.")

    elif args.cmd == "drag-test":
        start_x, start_y = center_x, center_y
        end_x, end_y = center_x + args.dx, center_y + args.dy
        print(f"Dragging from ({start_x}, {start_y}) to ({end_x}, {end_y}) in 2 seconds...")
        time.sleep(2)
        drag(start_x, start_y, end_x, end_y, duration=1.0)
        print("Dragged.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
