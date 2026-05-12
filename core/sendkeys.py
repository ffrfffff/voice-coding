from __future__ import annotations

import ctypes
import subprocess
import time
from ctypes import wintypes


KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_SCANCODE = 0x0008
INPUT_KEYBOARD = 1
MAPVK_VK_TO_VSC = 0

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
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [
            ("mi", MOUSEINPUT),
            ("ki", KEYBDINPUT),
            ("hi", HARDWAREINPUT),
        ]

    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUT_UNION)]


def send_enter() -> str:
    return _send_vk_sequence([VK_RETURN])


def send_escape() -> str:
    return _send_vk_sequence([VK_ESCAPE])


def send_ctrl_v() -> str:
    return _send_vk_sequence([VK_CONTROL, VK_V])


def send_shift_insert() -> str:
    return _send_vk_sequence([VK_SHIFT, VK_INSERT])


def _send_vk_sequence(keys: list[int]) -> str:
    ok, detail = _try_send_input_sequence(keys, use_scan_codes=True)
    if ok:
        time.sleep(0.05)
        return "SendInput(scan): " + "; ".join(detail)

    vk_ok, vk_detail = _try_send_input_sequence(keys, use_scan_codes=False)
    if vk_ok:
        time.sleep(0.05)
        return "SendInput(vk): " + "; ".join(vk_detail)

    fallback = _fallback_sendkeys(keys)
    _send_keys(fallback)
    return "WScript.SendKeys fallback: " + fallback + " after " + "; ".join(detail + vk_detail)


def _try_send_input_sequence(keys: list[int], use_scan_codes: bool) -> tuple[bool, list[str]]:
    detail: list[str] = []
    for key in keys:
        ok, item_detail = _send_one_key(key, 0, use_scan_codes)
        detail.append(f"{_key_name(key)} down {item_detail}")
        if not ok:
            return False, detail
        time.sleep(0.05)
    for key in reversed(keys):
        ok, item_detail = _send_one_key(key, KEYEVENTF_KEYUP, use_scan_codes)
        detail.append(f"{_key_name(key)} up {item_detail}")
        if not ok:
            return False, detail
        time.sleep(0.05)
    return True, detail


def _send_one_key(vk: int, flags: int, use_scan_codes: bool) -> tuple[bool, str]:
    input_item = _keyboard_input(vk, flags, use_scan_codes)
    ctypes.windll.kernel32.SetLastError(0)
    sent = ctypes.windll.user32.SendInput(1, ctypes.byref(input_item), ctypes.sizeof(INPUT))
    error = ctypes.windll.kernel32.GetLastError()
    return sent == 1, f"sent={sent} err={error}"


def _keyboard_input(vk: int, flags: int, use_scan_codes: bool) -> INPUT:
    scan = 0
    input_vk = vk
    if use_scan_codes:
        scan = ctypes.windll.user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
        input_vk = 0
        flags |= KEYEVENTF_SCANCODE
    if vk == VK_INSERT:
        flags |= KEYEVENTF_EXTENDEDKEY
    return INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(input_vk, scan, flags, 0, 0))


def _key_name(vk: int) -> str:
    names = {
        VK_CONTROL: "Ctrl",
        VK_SHIFT: "Shift",
        VK_ESCAPE: "Esc",
        VK_INSERT: "Insert",
        VK_RETURN: "Enter",
        VK_V: "V",
    }
    return names.get(vk, f"VK{vk}")


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
