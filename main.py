"""番茄钟 — Pomodoro Timer for Windows.

Zero third-party dependencies. Uses tkinter (stdlib) + winsound (Windows built-in).

Run:
    python main.py
"""

import json
import os
import sys
import tkinter as tk

from pomodoro.timer import PomodoroTimer
from pomodoro.ui import PomodoroUI

CONFIG_PATH = os.path.expanduser("~/.pomodoro_config.json")


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(config: dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except OSError:
        pass  # non-critical


def main():
    config = load_config()

    root = tk.Tk()
    timer = PomodoroTimer()
    ui = PomodoroUI(root, timer, config)

    def on_quit():
        save_config(ui.get_config())
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", ui._on_close)

    # Save config on exit even if user closes via tray quit
    orig_quit = ui._quit_app

    def _quit_with_save():
        save_config(ui.get_config())
        orig_quit()

    ui._quit_app = _quit_with_save

    root.mainloop()


if __name__ == "__main__":
    main()
