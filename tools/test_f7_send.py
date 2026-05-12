from __future__ import annotations

import threading
import time
import tkinter as tk
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.sendkeys import send_enter


def main() -> int:
    root = tk.Tk()
    root.title("F7 Enter Test")
    root.geometry("520x220")

    label = tk.Label(root, text="This window will test whether synthetic Enter reaches the focused text box.")
    label.pack(padx=12, pady=(12, 6))

    text = tk.Text(root, height=6, width=60)
    text.pack(padx=12, pady=6)
    text.insert("1.0", "start")
    text.focus_set()
    root.lift()
    root.attributes("-topmost", True)
    root.after(300, lambda: root.attributes("-topmost", False))
    root.after(350, text.focus_force)

    result = tk.StringVar(value="waiting")
    tk.Label(root, textvariable=result).pack(pady=6)

    def run_test() -> None:
        time.sleep(1.5)
        send_enter()
        time.sleep(0.4)
        content = text.get("1.0", "end")
        if "\n" in content.strip("\n"):
            result.set("PASS: Enter reached the text box.")
        else:
            result.set("FAIL: Enter did not reach the text box.")
        root.after(1200, root.destroy)

    threading.Thread(target=run_test, daemon=True).start()
    root.after(5000, root.destroy)
    root.mainloop()
    print(result.get())
    return 0 if result.get().startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
