from __future__ import annotations

import ctypes
import time
from ctypes import wintypes
from typing import Union

# --- Windows API Constants and Structs ---

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_ABSOLUTE = 0x8000

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("union", INPUT_UNION),
    ]


def _send_input(inputs: list[INPUT]):
    n_inputs = len(inputs)
    lp_inputs = (INPUT * n_inputs)(*inputs)
    cb_size = ctypes.sizeof(INPUT)
    ctypes.windll.user32.SendInput(n_inputs, lp_inputs, cb_size)


def _get_screen_size() -> tuple[int, int]:
    """Get primary screen resolution."""
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def _to_absolute_coords(x: int, y: int) -> tuple[int, int]:
    """Convert pixel coordinates to normalized absolute coordinates (0-65535)."""
    width, height = _get_screen_size()
    # Windows expects 65535 as the max value for absolute coordinates
    abs_x = int(x * 65535 / width)
    abs_y = int(y * 65535 / height)
    return abs_x, abs_y


# --- Public API ---


def move_mouse(x: int, y: int):
    """Move mouse to absolute screen coordinates (x, y)."""
    abs_x, abs_y = _to_absolute_coords(x, y)
    mi = MOUSEINPUT(
        dx=abs_x,
        dy=abs_y,
        mouseData=0,
        dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
        time=0,
        dwExtraInfo=0,
    )
    inp = INPUT(type=INPUT_MOUSE, union=INPUT_UNION(mi=mi))
    _send_input([inp])


def mouse_down(left: bool = True):
    """Press mouse button down."""
    flags = MOUSEEVENTF_LEFTDOWN if left else MOUSEEVENTF_RIGHTDOWN
    mi = MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=flags, time=0, dwExtraInfo=0)
    inp = INPUT(type=INPUT_MOUSE, union=INPUT_UNION(mi=mi))
    _send_input([inp])


def mouse_up(left: bool = True):
    """Release mouse button."""
    flags = MOUSEEVENTF_LEFTUP if left else MOUSEEVENTF_RIGHTUP
    mi = MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=flags, time=0, dwExtraInfo=0)
    inp = INPUT(type=INPUT_MOUSE, union=INPUT_UNION(mi=mi))
    _send_input([inp])


def click_at(x: int, y: int, duration: float = 0.05):
    """Move to (x, y) and click."""
    move_mouse(x, y)
    # Small sleep to ensure move registers before click
    time.sleep(0.02)
    mouse_down()
    time.sleep(duration)
    mouse_up()


def drag(start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5):
    """Drag from start to end over a duration."""
    move_mouse(start_x, start_y)
    time.sleep(0.05)
    mouse_down()
    time.sleep(0.05)

    # Interpolate movement
    steps = max(10, int(duration * 60))  # 60 updates per second approx
    for i in range(steps):
        t = (i + 1) / steps
        curr_x = int(start_x + (end_x - start_x) * t)
        curr_y = int(start_y + (end_y - start_y) * t)
        move_mouse(curr_x, curr_y)
        time.sleep(duration / steps)

    # Ensure we land exactly on end
    move_mouse(end_x, end_y)
    time.sleep(0.05)
    mouse_up()
