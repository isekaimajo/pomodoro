"""Tkinter UI for the Pomodoro timer."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import winsound

from .timer import PomodoroTimer, State


# ---- color scheme ----
BG = "#1e1e2e"
SURFACE = "#2a2a3c"
TEXT = "#cdd6f4"
ACCENT_RED = "#e74c3c"
ACCENT_GREEN = "#2ecc71"
ACCENT_BLUE = "#89b4fa"
PROGRESS_BG = "#3a3a50"
BTN_BG = "#3a3a50"
BTN_ACTIVE = "#4a4a60"


class PomodoroUI:
    def __init__(self, root: tk.Tk, timer: PomodoroTimer, config: dict | None = None,
                 persist_config: callable | None = None):
        self.root = root
        self.timer = timer
        self.config = config or {}
        self._persist_config = persist_config
        self._after_id = None
        self._tray_window = None
        self._tray_label = None
        self._settings_window = None
        self._style = None
        self.dot_labels = []

        self._setup_window()
        self._build_ui()
        self._wire_callbacks()
        self._apply_config()
        self._refresh()

    # ================================================================
    # Window setup
    # ================================================================
    def _setup_window(self):
        self.root.title("番茄钟")
        self.root.geometry("360x500")
        self.root.minsize(300, 420)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # always-on-top
        self.always_on_top = tk.BooleanVar(value=False)

        # try setting an icon (no-op if file missing)
        try:
            self.root.iconbitmap(default="tomato.ico")
        except Exception:
            pass

    # ================================================================
    # Build UI
    # ================================================================
    def _build_ui(self):
        # --- title ---
        title_frame = tk.Frame(self.root, bg=BG)
        title_frame.pack(pady=(20, 5))
        tk.Label(
            title_frame, text="🍅 番茄钟", font=("Segoe UI", 18, "bold"),
            fg=ACCENT_RED, bg=BG,
        ).pack()

        # --- mode label ---
        self.mode_label = tk.Label(
            self.root, text="准备就绪", font=("Segoe UI", 12),
            fg=TEXT, bg=BG,
        )
        self.mode_label.pack(pady=(0, 10))

        # --- countdown ---
        self.countdown_label = tk.Label(
            self.root, text="25:00", font=("Consolas", 48, "bold"),
            fg=TEXT, bg=BG,
        )
        self.countdown_label.pack(pady=(0, 10))

        # --- progress bar ---
        self._style = ttk.Style()
        self._style.theme_use("clam")
        self._style.configure(
            "Pomodoro.Horizontal.TProgressbar",
            background=ACCENT_RED, troughcolor=PROGRESS_BG,
            borderwidth=0, lightcolor=ACCENT_RED, darkcolor=ACCENT_RED,
        )
        self.progress = ttk.Progressbar(
            self.root, orient="horizontal", length=280, mode="determinate",
            style="Pomodoro.Horizontal.TProgressbar",
        )
        self.progress.pack(pady=(0, 15))

        # --- tomato dots ---
        self.dots_frame = tk.Frame(self.root, bg=BG)
        self.dots_frame.pack(pady=(0, 15))
        self._build_dot_labels()

        # --- control buttons ---
        btn_frame = tk.Frame(self.root, bg=BG)
        btn_frame.pack(pady=(0, 10))

        self.start_btn = self._create_button(
            btn_frame, "▶  开始", self._on_start, accent=True,
        )

        self.pause_btn = self._create_button(
            btn_frame, "⏸  暂停", self._on_pause,
        )

        self.reset_btn = self._create_button(
            btn_frame, "↺  重置", self._on_reset,
        )

        self.skip_btn = self._create_button(
            btn_frame, "⏭  跳过", self._on_skip,
        )

        # --- stats ---
        self.stats_label = tk.Label(
            self.root, text="总完成: 0 个番茄", font=("Segoe UI", 10),
            fg="#6c7086", bg=BG,
        )
        self.stats_label.pack(pady=(10, 5))

        # --- bottom bar: settings + always-on-top ---
        bottom = tk.Frame(self.root, bg=BG)
        bottom.pack(side="bottom", fill="x", pady=10, padx=20)

        self.top_toggle = tk.Checkbutton(
            bottom, text="窗口置顶", variable=self.always_on_top,
            command=self._toggle_always_on_top,
            bg=BG, fg="#6c7086", selectcolor=BG,
            activebackground=BG, activeforeground=TEXT,
        )
        self.top_toggle.pack(side="left")

        settings_btn = tk.Button(
            bottom, text="⚙  设置", font=("Segoe UI", 10),
            bg=BG, fg="#6c7086", activebackground=BG,
            activeforeground=TEXT, relief="flat", padx=8,
            cursor="hand2", borderwidth=0,
            command=self._open_settings,
        )
        settings_btn.pack(side="right")

    def _create_button(self, parent, text, command, accent=False):
        """Create a styled control button, pack it, and return it."""
        bg = ACCENT_RED if accent else BTN_BG
        abg = "#c0392b" if accent else BTN_ACTIVE
        btn = tk.Button(
            parent, text=text, font=("Segoe UI", 11),
            bg=bg, fg="#fff" if accent else TEXT,
            activebackground=abg, activeforeground="#fff" if accent else TEXT,
            relief="flat", padx=14, pady=6,
            cursor="hand2", borderwidth=0,
            command=command,
        )
        btn.pack(side="left", padx=4)
        return btn

    def _build_dot_labels(self):
        """Create dot Label widgets once (reused by _refresh_dots)."""
        for w in self.dots_frame.winfo_children():
            w.destroy()
        self.dot_labels.clear()
        for _ in range(self.timer.long_break_interval):
            lbl = tk.Label(
                self.dots_frame, font=("Segoe UI", 18),
                bg=BG,
            )
            lbl.pack(side="left", padx=4)
            self.dot_labels.append(lbl)

    # ================================================================
    # Callbacks from timer
    # ================================================================
    def _wire_callbacks(self):
        self.timer.on_tick(self._refresh)
        self.timer.on_complete(self._on_timer_complete)

    def _on_timer_complete(self):
        self._play_sound()
        self._flash_window()

    def _play_sound(self):
        try:
            winsound.Beep(800, 200)
            self.root.after(150, lambda: winsound.Beep(1000, 200))
            self.root.after(300, lambda: winsound.Beep(1200, 400))
        except Exception:
            pass

    def _flash_window(self):
        try:
            self.root.attributes("-topmost", True)
            self.root.after(500, lambda: self.root.attributes("-topmost", self.always_on_top.get()))
        except Exception:
            pass

    # ================================================================
    # Button actions
    # ================================================================
    def _on_start(self):
        if self.timer.is_idle or self.timer.is_paused:
            self.timer.start()
            self._start_ticking()
        self._refresh()

    def _on_pause(self):
        self.timer.pause()
        self._stop_ticking()
        self._refresh()

    def _on_reset(self):
        self.timer.reset()
        self._stop_ticking()
        self._refresh()

    def _on_skip(self):
        """Skip the current session and advance to the next state."""
        if self.timer.is_running:
            self.timer.skip()
            self._refresh()
            if self.timer.is_running:
                self._start_ticking()

    # ================================================================
    # Tick loop
    # ================================================================
    def _start_ticking(self):
        self._stop_ticking()
        self._schedule_tick()

    def _schedule_tick(self):
        if self.timer.is_running:
            self._after_id = self.root.after(1000, self._do_tick)

    def _do_tick(self):
        self.timer.tick()
        if self.timer.is_running:
            self._schedule_tick()
        else:
            self._stop_ticking()
            self._refresh()

    def _stop_ticking(self):
        if self._after_id:
            self.root.after_cancel(self._after_id)
            self._after_id = None

    # ================================================================
    # Refresh display
    # ================================================================
    def _refresh(self):
        t = self.timer

        # mode label
        mode_texts = {
            State.IDLE: "准备就绪",
            State.FOCUS: "🔴 专注",
            State.SHORT_BREAK: "🟢 短休息",
            State.LONG_BREAK: "🔵 长休息",
            State.PAUSED: "⏸  已暂停",
        }
        self.mode_label.config(text=mode_texts.get(t.state, ""))

        # countdown
        self.countdown_label.config(text=f"{t.minutes:02d}:{t.seconds:02d}")

        # progress bar
        self.progress["value"] = t.progress * 100

        # progress bar color by state (reuse stored style instance)
        if t.is_break:
            color = ACCENT_GREEN
        else:
            color = ACCENT_RED
        self._style.configure("Pomodoro.Horizontal.TProgressbar", background=color)

        # tomato dots
        self._refresh_dots()

        # button states
        if t.is_idle:
            self.start_btn.config(text="▶  开始")
        elif t.is_paused:
            self.start_btn.config(text="▶  继续")
        else:
            self.start_btn.config(text="▶  开始")

        # stats
        self.stats_label.config(text=f"总完成: {t.total_pomodoros} 个番茄")

        # update tray label if visible
        if self._tray_window and self._tray_window.winfo_exists() and self._tray_label:
            self._tray_label.config(text=f"🍅 {t.minutes:02d}:{t.seconds:02d}")

    def _refresh_dots(self):
        interval = self.timer.long_break_interval
        completed = self.timer.session

        # Rebuild labels if interval changed (e.g. after settings save)
        if len(self.dot_labels) != interval:
            self._build_dot_labels()

        for i, lbl in enumerate(self.dot_labels):
            if i < completed:
                lbl.config(text="🍅", fg=ACCENT_RED)
            else:
                lbl.config(text="○", fg="#6c7086")

    # ================================================================
    # Always on top
    # ================================================================
    def _toggle_always_on_top(self):
        self.root.attributes("-topmost", self.always_on_top.get())

    # ================================================================
    # Settings dialog
    # ================================================================
    def _open_settings(self):
        if self._settings_window and self._settings_window.winfo_exists():
            self._settings_window.lift()
            self._settings_window.focus_force()
            return

        self._settings_window = tk.Toplevel(self.root)
        self._settings_window.title("设置")
        self._settings_window.geometry("300x260")
        self._settings_window.configure(bg=SURFACE)
        self._settings_window.resizable(False, False)
        self._settings_window.transient(self.root)

        # center on parent
        self._settings_window.update_idletasks()
        px = self.root.winfo_x() + (self.root.winfo_width() - 300) // 2
        py = self.root.winfo_y() + (self.root.winfo_height() - 260) // 2
        self._settings_window.geometry(f"+{px}+{py}")

        tk.Label(
            self._settings_window, text="设置", font=("Segoe UI", 14, "bold"),
            fg=TEXT, bg=SURFACE,
        ).pack(pady=(15, 10))

        # setting rows
        focus_var = tk.IntVar(value=self.timer.focus_minutes)
        self._add_setting_row(self._settings_window, "专注时长 (分钟)", focus_var, 1, 120)

        short_var = tk.IntVar(value=self.timer.short_break_minutes)
        self._add_setting_row(self._settings_window, "短休息时长 (分钟)", short_var, 1, 60)

        long_var = tk.IntVar(value=self.timer.long_break_minutes)
        self._add_setting_row(self._settings_window, "长休息时长 (分钟)", long_var, 1, 120)

        interval_var = tk.IntVar(value=self.timer.long_break_interval)
        self._add_setting_row(self._settings_window, "长休息间隔 (轮)", interval_var, 1, 10)

        # save button
        def _save():
            self.timer.focus_minutes = focus_var.get()
            self.timer.short_break_minutes = short_var.get()
            self.timer.long_break_minutes = long_var.get()
            self.timer.long_break_interval = interval_var.get()
            self.timer.reset()
            self._stop_ticking()
            self._refresh()
            self._save_config()
            if self._persist_config:
                self._persist_config(self.config)
            self._settings_window.destroy()
            self._settings_window = None

        tk.Button(
            self._settings_window, text="保存", font=("Segoe UI", 11, "bold"),
            bg=ACCENT_RED, fg="#fff", activebackground="#c0392b",
            activeforeground="#fff", relief="flat", padx=30, pady=5,
            cursor="hand2", borderwidth=0, command=_save,
        ).pack(pady=(15, 10))

        def _on_settings_close():
            self._settings_window.destroy()
            self._settings_window = None

        self._settings_window.protocol("WM_DELETE_WINDOW", _on_settings_close)

    def _add_setting_row(self, parent, label_text, variable, from_, to):
        """Create a single Label + Spinbox row for the settings dialog."""
        frame = tk.Frame(parent, bg=SURFACE)
        frame.pack(fill="x", padx=15, pady=5)
        tk.Label(
            frame, text=label_text, fg=TEXT, bg=SURFACE, font=("Segoe UI", 10),
        ).pack(side="left")
        tk.Spinbox(
            frame, from_=from_, to=to, textvariable=variable, width=5,
            font=("Segoe UI", 10), bg=SURFACE, fg=TEXT,
            buttonbackground=BTN_BG, justify="center",
        ).pack(side="right")

    # ================================================================
    # Config persistence
    # ================================================================
    def _apply_config(self):
        if not self.config:
            return
        self.timer.focus_minutes = self.config.get("focus_minutes", 25)
        self.timer.short_break_minutes = self.config.get("short_break_minutes", 5)
        self.timer.long_break_minutes = self.config.get("long_break_minutes", 15)
        self.timer.long_break_interval = self.config.get("long_break_interval", 4)
        self.always_on_top.set(self.config.get("always_on_top", False))
        self._toggle_always_on_top()
        self.timer.reset()

    def _save_config(self):
        self.config = {
            "focus_minutes": self.timer.focus_minutes,
            "short_break_minutes": self.timer.short_break_minutes,
            "long_break_minutes": self.timer.long_break_minutes,
            "long_break_interval": self.timer.long_break_interval,
            "always_on_top": self.always_on_top.get(),
        }

    def get_config(self) -> dict:
        return self.config

    # ================================================================
    # Tray / minimize behavior
    # ================================================================
    def _on_close(self):
        """Minimize to a small floating indicator instead of quitting."""
        self.root.withdraw()
        self._show_tray()

    def _show_tray(self):
        if self._tray_window and self._tray_window.winfo_exists():
            return

        self._tray_window = tk.Toplevel(self.root)
        self._tray_window.overrideredirect(True)
        self._tray_window.configure(bg=SURFACE)
        self._tray_window.attributes("-topmost", True)
        self._tray_window.geometry("100x40+%d+%d" % (
            self.root.winfo_screenwidth() - 110,
            self.root.winfo_screenheight() - 80,
        ))

        t = self.timer
        self._tray_label = tk.Label(
            self._tray_window,
            text=f"🍅 {t.minutes:02d}:{t.seconds:02d}",
            font=("Consolas", 12, "bold"), fg=ACCENT_RED, bg=SURFACE,
        )
        self._tray_label.pack(expand=True)

        # click to restore
        def _restore(_event=None):
            self._tray_label = None
            self._tray_window.destroy()
            self._tray_window = None
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()

        self._tray_window.bind("<Button-1>", _restore)
        self._tray_label.bind("<Button-1>", _restore)

        # belt-and-suspenders: handle external tray destruction
        def _on_tray_destroy():
            self._tray_label = None
            self._tray_window = None

        self._tray_window.protocol("WM_DELETE_WINDOW", _on_tray_destroy)

        # right-click menu
        menu = tk.Menu(self._tray_window, tearoff=0, bg=SURFACE, fg=TEXT)
        menu.add_command(label="恢复窗口", command=_restore)
        menu.add_separator()
        menu.add_command(label="退出", command=self._quit_app)

        def _right_click(event):
            menu.post(event.x_root, event.y_root)

        self._tray_window.bind("<Button-3>", _right_click)
        self._tray_label.bind("<Button-3>", _right_click)

    def _quit_app(self):
        self._stop_ticking()
        if self._persist_config:
            self._persist_config(self.config)
        if self._tray_window:
            self._tray_window.destroy()
            self._tray_window = None
            self._tray_label = None
        self.root.destroy()
