"""
Auto Typer — A desktop app that simulates real keyboard typing.
Paste your text, switch to any window, and watch it type automatically.

Hotkeys:
    Ctrl+Shift+T  → Start typing
    Escape         → Stop typing immediately

Usage:
    python autotyper.py
"""

import customtkinter as ctk
import pyautogui
import threading
import time
from pynput import keyboard as pynput_keyboard


# ─── Configuration ──────────────────────────────────────────────────────────────

APP_TITLE = "⌨ Auto Typer"
APP_SIZE = "620x700"
MIN_SIZE = (520, 600)

# Theme colors
COLOR_BG = "#0f0f14"
COLOR_CARD = "#1a1a24"
COLOR_BORDER = "#2a2a3a"
COLOR_ACCENT = "#7c5cfc"
COLOR_ACCENT_HOVER = "#6a48e8"
COLOR_ACCENT_LIGHT = "#9d85fc"
COLOR_DANGER = "#fc5c6c"
COLOR_DANGER_HOVER = "#e84858"
COLOR_TEXT = "#e8e6f0"
COLOR_TEXT_DIM = "#8884a0"
COLOR_SUCCESS = "#4ceca0"
COLOR_COUNTDOWN = "#ff9f43"

FONT_FAMILY = "Segoe UI"

# pyautogui safety
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


# ─── AutoTyperApp ───────────────────────────────────────────────────────────────

class AutoTyperApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # ── Window setup ──
        self.title(APP_TITLE)
        self.geometry(APP_SIZE)
        self.minsize(*MIN_SIZE)
        self.configure(fg_color=COLOR_BG)
        self.resizable(True, True)

        # ── State ──
        self._typing = False
        self._stop_event = threading.Event()
        self._typing_thread = None
        self._countdown_active = False

        # ── Build UI ──
        self._build_header()
        self._build_text_area()
        self._build_controls()
        self._build_status_bar()
        self._build_countdown_overlay()

        # ── Global hotkey listener ──
        self._hotkey_listener = None
        self._start_hotkey_listener()

        # ── Handle window close ──
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ────────────────────────────────────────────────────────────────────────
    # UI Building
    # ────────────────────────────────────────────────────────────────────────

    def _build_header(self):
        """App title and subtitle."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 4))

        title = ctk.CTkLabel(
            header,
            text="⌨  Auto Typer",
            font=(FONT_FAMILY, 26, "bold"),
            text_color=COLOR_TEXT,
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            header,
            text="Paste text below → set speed & delay → press Start → switch windows",
            font=(FONT_FAMILY, 12),
            text_color=COLOR_TEXT_DIM,
        )
        subtitle.pack(anchor="w", pady=(2, 0))

    def _build_text_area(self):
        """Text input area with a card-like container."""
        card = ctk.CTkFrame(
            self,
            fg_color=COLOR_CARD,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        card.pack(fill="both", expand=True, padx=24, pady=(12, 8))

        # Label
        label = ctk.CTkLabel(
            card,
            text="TEXT TO TYPE",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLOR_TEXT_DIM,
        )
        label.pack(anchor="w", padx=16, pady=(14, 4))

        # Textbox
        self.textbox = ctk.CTkTextbox(
            card,
            font=(FONT_FAMILY, 14),
            fg_color="#12121c",
            text_color=COLOR_TEXT,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER,
            wrap="word",
        )
        self.textbox.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        # Character count
        self.char_count_label = ctk.CTkLabel(
            card,
            text="0 characters",
            font=(FONT_FAMILY, 10),
            text_color=COLOR_TEXT_DIM,
        )
        self.char_count_label.pack(anchor="e", padx=16, pady=(0, 10))

        # Bind key events for live character count
        self.textbox.bind("<KeyRelease>", self._update_char_count)
        self.textbox.bind("<<Modified>>", self._update_char_count)
        # Also poll on focus to catch paste events
        self.textbox.bind("<FocusIn>", self._update_char_count)
        self.textbox.bind("<ButtonRelease>", self._update_char_count)

    def _build_controls(self):
        """Speed slider, delay picker, and action buttons."""
        controls_card = ctk.CTkFrame(
            self,
            fg_color=COLOR_CARD,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        controls_card.pack(fill="x", padx=24, pady=(4, 8))

        # ── Row 1: Speed ──
        speed_frame = ctk.CTkFrame(controls_card, fg_color="transparent")
        speed_frame.pack(fill="x", padx=16, pady=(14, 4))

        speed_label = ctk.CTkLabel(
            speed_frame,
            text="TYPING SPEED",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLOR_TEXT_DIM,
        )
        speed_label.pack(side="left")

        self.speed_value_label = ctk.CTkLabel(
            speed_frame,
            text="50 chars/sec",
            font=(FONT_FAMILY, 11),
            text_color=COLOR_ACCENT_LIGHT,
        )
        self.speed_value_label.pack(side="right")

        self.speed_slider = ctk.CTkSlider(
            controls_card,
            from_=5,
            to=200,
            number_of_steps=39,
            command=self._on_speed_change,
            fg_color=COLOR_BORDER,
            progress_color=COLOR_ACCENT,
            button_color=COLOR_ACCENT_LIGHT,
            button_hover_color=COLOR_ACCENT,
        )
        self.speed_slider.set(50)
        self.speed_slider.pack(fill="x", padx=16, pady=(0, 10))

        # ── Row 2: Delay + Buttons ──
        row2 = ctk.CTkFrame(controls_card, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=(0, 14))

        # Delay
        delay_label = ctk.CTkLabel(
            row2,
            text="DELAY",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLOR_TEXT_DIM,
        )
        delay_label.pack(side="left", padx=(0, 8))

        self.delay_var = ctk.StringVar(value="5")
        self.delay_menu = ctk.CTkOptionMenu(
            row2,
            values=["3", "5", "7", "10"],
            variable=self.delay_var,
            width=80,
            font=(FONT_FAMILY, 12),
            fg_color="#12121c",
            button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT_HOVER,
            dropdown_fg_color=COLOR_CARD,
            dropdown_hover_color=COLOR_ACCENT,
            dropdown_text_color=COLOR_TEXT,
        )
        self.delay_menu.pack(side="left")

        sec_label = ctk.CTkLabel(
            row2,
            text="sec",
            font=(FONT_FAMILY, 11),
            text_color=COLOR_TEXT_DIM,
        )
        sec_label.pack(side="left", padx=(4, 0))

        # Fix IDE Indent Checkbox
        self.smart_indent_cb = ctk.CTkCheckBox(
            row2,
            text="Fix IDE Indent",
            font=(FONT_FAMILY, 11),
            text_color=COLOR_TEXT_DIM,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            border_color=COLOR_BORDER,
            checkbox_width=18,
            checkbox_height=18,
        )
        self.smart_indent_cb.pack(side="left", padx=(16, 0))
        self.smart_indent_cb.select()

        # Stop button
        self.stop_btn = ctk.CTkButton(
            row2,
            text="■  Stop",
            width=90,
            height=36,
            font=(FONT_FAMILY, 13, "bold"),
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_HOVER,
            corner_radius=8,
            command=self._stop_typing,
            state="disabled",
        )
        self.stop_btn.pack(side="right", padx=(8, 0))

        # Start button
        self.start_btn = ctk.CTkButton(
            row2,
            text="▶  Start Typing",
            width=140,
            height=36,
            font=(FONT_FAMILY, 13, "bold"),
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            corner_radius=8,
            command=self._start_typing,
        )
        self.start_btn.pack(side="right")

    def _build_status_bar(self):
        """Progress bar and status text at the bottom."""
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.pack(fill="x", padx=24, pady=(0, 6))

        self.progress_bar = ctk.CTkProgressBar(
            status_frame,
            fg_color=COLOR_BORDER,
            progress_color=COLOR_ACCENT,
            height=6,
            corner_radius=3,
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(0, 6))

        bottom_row = ctk.CTkFrame(status_frame, fg_color="transparent")
        bottom_row.pack(fill="x")

        self.status_label = ctk.CTkLabel(
            bottom_row,
            text="Ready — paste your text and press Start",
            font=(FONT_FAMILY, 11),
            text_color=COLOR_TEXT_DIM,
        )
        self.status_label.pack(side="left")

        hotkey_hint = ctk.CTkLabel(
            bottom_row,
            text="Ctrl+Shift+T  start  •  Esc  stop",
            font=(FONT_FAMILY, 10),
            text_color=COLOR_TEXT_DIM,
        )
        hotkey_hint.pack(side="right")

    def _build_countdown_overlay(self):
        """A semi-transparent overlay that shows the countdown number."""
        self.countdown_overlay = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        # Not packed yet — shown only during countdown

        self.countdown_number = ctk.CTkLabel(
            self.countdown_overlay,
            text="",
            font=(FONT_FAMILY, 72, "bold"),
            text_color=COLOR_COUNTDOWN,
        )
        self.countdown_number.pack(expand=True)

        self.countdown_subtext = ctk.CTkLabel(
            self.countdown_overlay,
            text="Switch to your target window now!",
            font=(FONT_FAMILY, 14),
            text_color=COLOR_TEXT_DIM,
        )
        self.countdown_subtext.pack(pady=(0, 40))

    # ────────────────────────────────────────────────────────────────────────
    # Event Handlers
    # ────────────────────────────────────────────────────────────────────────

    def _update_char_count(self, event=None):
        """Update the character count label."""
        text = self.textbox.get("1.0", "end-1c")
        count = len(text)
        self.char_count_label.configure(text=f"{count:,} characters")

    def _on_speed_change(self, value):
        """Update speed label when slider moves."""
        speed = int(value)
        self.speed_value_label.configure(text=f"{speed} chars/sec")

    # ────────────────────────────────────────────────────────────────────────
    # Typing Engine
    # ────────────────────────────────────────────────────────────────────────

    def _start_typing(self):
        """Begin the countdown, then type."""
        text = self.textbox.get("1.0", "end-1c").strip()
        
        if hasattr(self, 'smart_indent_cb') and self.smart_indent_cb.get():
            # Remove leading spaces and tabs from each line to prevent IDE double-indentation
            text = "\n".join(line.lstrip(" \t") for line in text.split("\n"))

        if not text:
            self._set_status("⚠ Nothing to type — paste some text first", COLOR_COUNTDOWN)
            return

        if self._typing or self._countdown_active:
            return

        self._stop_event.clear()
        self._countdown_active = True

        # Disable start, enable stop
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)

        # Start countdown in a thread
        delay = int(self.delay_var.get())
        thread = threading.Thread(target=self._countdown_then_type, args=(text, delay), daemon=True)
        thread.start()

    def _countdown_then_type(self, text: str, delay: int):
        """Run countdown, then type the text."""
        # ── Countdown ──
        self.after(0, lambda: self._show_countdown_overlay(True))

        for remaining in range(delay, 0, -1):
            if self._stop_event.is_set():
                self.after(0, lambda: self._show_countdown_overlay(False))
                self.after(0, self._reset_ui)
                return
            self.after(0, lambda r=remaining: self.countdown_number.configure(text=str(r)))
            self.after(0, lambda r=remaining: self._set_status(
                f"⏱ Starting in {r} seconds — switch to your target window!", COLOR_COUNTDOWN
            ))
            time.sleep(1)

        self.after(0, lambda: self._show_countdown_overlay(False))
        self._countdown_active = False

        # ── Type ──
        self._typing = True
        speed = int(self.speed_slider.get())
        interval = 1.0 / speed if speed > 0 else 0.02
        total = len(text)

        self.after(0, lambda: self._set_status(f"⌨ Typing... 0/{total:,}", COLOR_ACCENT_LIGHT))

        for i, char in enumerate(text):
            if self._stop_event.is_set():
                self.after(0, lambda idx=i: self._set_status(
                    f"⏹ Stopped at {idx:,}/{total:,} characters", COLOR_DANGER
                ))
                self.after(0, self._reset_ui)
                return

            # Simulate the keystroke
            self._type_char(char)

            # Update progress
            progress = (i + 1) / total
            typed = i + 1
            self.after(0, lambda p=progress: self.progress_bar.set(p))
            if typed % max(1, total // 50) == 0 or typed == total:
                self.after(0, lambda t=typed: self._set_status(
                    f"⌨ Typing... {t:,}/{total:,}", COLOR_ACCENT_LIGHT
                ))

            time.sleep(interval)

        # ── Done ──
        self._typing = False
        self.after(0, lambda: self.progress_bar.set(1.0))
        self.after(0, lambda: self._set_status(
            f"✓ Done! Typed {total:,} characters", COLOR_SUCCESS
        ))
        self.after(0, self._reset_ui)

    def _type_char(self, char: str):
        """Type a single character using pyautogui."""
        if char == "\n":
            pyautogui.press("enter")
        elif char == "\t":
            pyautogui.press("tab")
        else:
            try:
                pyautogui.write(char, interval=0)
            except Exception:
                # Fallback for special/unicode characters — use clipboard approach
                try:
                    import pyperclip
                    pyperclip.copy(char)
                    pyautogui.hotkey("ctrl", "v")
                except Exception:
                    pass  # Skip unsupported characters

    def _stop_typing(self):
        """Stop typing immediately."""
        self._stop_event.set()
        self._countdown_active = False

    def _reset_ui(self):
        """Re-enable the start button and disable stop."""
        self._typing = False
        self._countdown_active = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def _set_status(self, text: str, color: str = COLOR_TEXT_DIM):
        """Update the status label."""
        self.status_label.configure(text=text, text_color=color)

    def _show_countdown_overlay(self, show: bool):
        """Show or hide the countdown overlay."""
        if show:
            self.countdown_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.countdown_overlay.configure(fg_color=COLOR_BG)
            self.countdown_overlay.lift()
        else:
            self.countdown_overlay.place_forget()
            self.countdown_number.configure(text="")

    # ────────────────────────────────────────────────────────────────────────
    # Global Hotkeys (pynput)
    # ────────────────────────────────────────────────────────────────────────

    def _start_hotkey_listener(self):
        """Listen for global hotkeys using pynput."""
        # Track currently pressed keys
        self._pressed_keys = set()

        def on_press(key):
            self._pressed_keys.add(key)

            # Ctrl+Shift+T → Start
            ctrl = (
                pynput_keyboard.Key.ctrl_l in self._pressed_keys
                or pynput_keyboard.Key.ctrl_r in self._pressed_keys
            )
            shift = (
                pynput_keyboard.Key.shift_l in self._pressed_keys
                or pynput_keyboard.Key.shift_r in self._pressed_keys
            )
            try:
                t_pressed = any(
                    (hasattr(k, "char") and k.char and k.char.lower() == "t")
                    for k in self._pressed_keys
                )
            except Exception:
                t_pressed = False

            if ctrl and shift and t_pressed:
                self.after(0, self._start_typing)

            # Escape → Stop
            if key == pynput_keyboard.Key.esc:
                if self._typing or self._countdown_active:
                    self.after(0, self._stop_typing)

        def on_release(key):
            self._pressed_keys.discard(key)

        self._hotkey_listener = pynput_keyboard.Listener(
            on_press=on_press, on_release=on_release
        )
        self._hotkey_listener.daemon = True
        self._hotkey_listener.start()

    # ────────────────────────────────────────────────────────────────────────
    # Cleanup
    # ────────────────────────────────────────────────────────────────────────

    def _on_close(self):
        """Clean shutdown."""
        self._stop_event.set()
        if self._hotkey_listener:
            self._hotkey_listener.stop()
        self.destroy()


# ─── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = AutoTyperApp()
    app.mainloop()
