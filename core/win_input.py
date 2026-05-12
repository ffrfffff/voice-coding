from __future__ import annotations

import ctypes
from ctypes import wintypes
import time


INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_RETURN = 0x0D
VK_LWIN = 0x5B
VK_H = 0x48
VK_V = 0x56
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]


def press_key(vk: int) -> None:
    _send_key(vk, False)
    _send_key(vk, True)


def press_combo(*vks: int) -> None:
    for vk in vks:
        _send_key(vk, False)
    time.sleep(0.03)
    for vk in reversed(vks):
        _send_key(vk, True)


def press_enter() -> None:
    press_key(VK_RETURN)


def press_ctrl_v() -> None:
    press_combo(VK_CONTROL, VK_V)


def press_win_h() -> None:
    press_combo(VK_LWIN, VK_H)


def _send_key(vk: int, key_up: bool) -> None:
    flags = KEYEVENTF_KEYUP if key_up else 0
    event = INPUT(
        type=INPUT_KEYBOARD,
        union=INPUT_UNION(ki=KEYBDINPUT(vk, 0, flags, 0, 0)),
    )
    sent = ctypes.windll.user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(event))
    if sent != 1:
        raise ctypes.WinError()
