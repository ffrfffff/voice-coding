from __future__ import annotations

import ctypes
import subprocess
import time
from ctypes import wintypes


KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1

VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_ESCAPE = 0x1B
VK_INSERT = 0x2D
VK_RETURN = 0x0D
VK_V = 0x56


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]

    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUT_UNION)]


def send_enter() -> None:
    _send_vk_sequence([VK_RETURN])


def send_escape() -> None:
    _send_vk_sequence([VK_ESCAPE])


def send_ctrl_v() -> None:
    _send_vk_sequence([VK_CONTROL, VK_V])


def send_shift_insert() -> None:
    _send_vk_sequence([VK_SHIFT, VK_INSERT])


def _send_vk_sequence(keys: list[int]) -> None:
    if _try_send_input(keys):
        time.sleep(0.05)
        return
    _send_keys(_fallback_sendkeys(keys))


def _try_send_input(keys: list[int]) -> bool:
    inputs = []
    for key in keys:
        inputs.append(_keyboard_input(key, 0))
    for key in reversed(keys):
        inputs.append(_keyboard_input(key, KEYEVENTF_KEYUP))

    array_type = INPUT * len(inputs)
    input_array = array_type(*inputs)
    sent = ctypes.windll.user32.SendInput(len(input_array), input_array, ctypes.sizeof(INPUT))
    return sent == len(inputs)


def _keyboard_input(vk: int, flags: int) -> INPUT:
    return INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(vk, 0, flags, 0, None))


def _fallback_sendkeys(keys: list[int]) -> str:
    if keys == [VK_CONTROL, VK_V]:
        return "^v"
    if keys == [VK_SHIFT, VK_INSERT]:
        return "+{INSERT}"
    if keys == [VK_RETURN]:
        return "{ENTER}"
    if keys == [VK_ESCAPE]:
        return "{ESC}"
    raise RuntimeError(f"Unsupported key sequence: {keys}")


def _send_keys(keys: str) -> None:
    escaped = keys.replace("'", "''")
    command = (
        "$wshell = New-Object -ComObject WScript.Shell;"
        "Start-Sleep -Milliseconds 80;"
        f"$wshell.SendKeys('{escaped}')"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=3,
        check=False,
    )
