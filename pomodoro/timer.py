"""Pomodoro timer core logic — state machine and countdown."""

from enum import Enum, auto


class State(Enum):
    IDLE = auto()
    FOCUS = auto()
    SHORT_BREAK = auto()
    LONG_BREAK = auto()
    PAUSED = auto()


class PomodoroTimer:
    def __init__(self):
        self.state = State.IDLE
        self._before_pause = None
        self.remaining = 0
        self.duration = 0
        self.session = 0  # completed focus sessions in current cycle (0-3)
        self.total_pomodoros = 0

        # configurable durations (seconds)
        self.focus_minutes = 25
        self.short_break_minutes = 5
        self.long_break_minutes = 15
        self.long_break_interval = 4  # every N focus sessions

        self._tick_callbacks = []
        self._complete_callbacks = []

    # ---- durations in seconds ----
    @property
    def focus_seconds(self):
        return self.focus_minutes * 60

    @property
    def short_break_seconds(self):
        return self.short_break_minutes * 60

    @property
    def long_break_seconds(self):
        return self.long_break_minutes * 60

    # ---- state helpers ----
    @property
    def is_idle(self):
        return self.state == State.IDLE

    @property
    def is_paused(self):
        return self.state == State.PAUSED

    @property
    def is_running(self):
        return self.state in (State.FOCUS, State.SHORT_BREAK, State.LONG_BREAK)

    @property
    def is_break(self):
        return self.state in (State.SHORT_BREAK, State.LONG_BREAK)

    # ---- progress ----
    @property
    def progress(self):
        """0.0 .. 1.0"""
        if self.duration == 0:
            return 0.0
        return 1.0 - (self.remaining / self.duration)

    @property
    def minutes(self):
        return self.remaining // 60

    @property
    def seconds(self):
        return self.remaining % 60

    # ---- callbacks ----
    def on_tick(self, fn):
        self._tick_callbacks.append(fn)

    def on_complete(self, fn):
        self._complete_callbacks.append(fn)

    def _notify_tick(self):
        for fn in self._tick_callbacks:
            fn()

    def _notify_complete(self):
        for fn in self._complete_callbacks:
            fn()

    # ---- actions ----
    def start(self):
        if self.state == State.IDLE:
            self._enter_focus()
        elif self.state == State.PAUSED and self._before_pause:
            self.state = self._before_pause
            self._before_pause = None

    def pause(self):
        if self.is_running:
            self._before_pause = self.state
            self.state = State.PAUSED

    def reset(self):
        self.state = State.IDLE
        self._before_pause = None
        self.remaining = self.focus_seconds
        self.duration = self.focus_seconds
        self.session = 0

    def skip(self):
        """Skip current session and move to the next state."""
        if self.is_running:
            self.remaining = 0
            self._advance()

    # ---- tick ----
    def tick(self):
        if not self.is_running:
            return
        self.remaining -= 1
        self._notify_tick()
        if self.remaining <= 0:
            self._advance()

    # ---- internal ----
    def _enter_focus(self):
        self.state = State.FOCUS
        self.remaining = self.focus_seconds
        self.duration = self.focus_seconds

    def _enter_short_break(self):
        self.state = State.SHORT_BREAK
        self.remaining = self.short_break_seconds
        self.duration = self.short_break_seconds

    def _enter_long_break(self):
        self.state = State.LONG_BREAK
        self.remaining = self.long_break_seconds
        self.duration = self.long_break_seconds

    def _advance(self):
        if self.state == State.FOCUS:
            self.session += 1
            self.total_pomodoros += 1
            if self.session >= self.long_break_interval:
                self.session = 0
                self._enter_long_break()
            else:
                self._enter_short_break()
        else:
            self._enter_focus()
        self._notify_complete()
