#!/usr/bin/env python3
"""
JBScrape UI — cross-platform graphical wrapper for JBScrape.
Works on macOS and Windows. Auto-detects platform and picks the right script.

macOS  → JBScrape.py          (Notes app output)
Windows → JBScrape_windows.py  (Notepad output)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import sys
import os

IS_WINDOWS = sys.platform == "win32"
IS_MAC     = sys.platform == "darwin"

# ── Palette — matches the screenshot's Catppuccin-ish dark charcoal ───────────
BG      = "#1e1e2e"   # base — deep charcoal, the wallpaper-matching bg
MANTLE  = "#181825"   # slightly darker, for panels/bars
CRUST   = "#11111b"   # darkest, titlebar / input bg
SURFACE = "#313244"   # surface0, subtle borders and hover
OVERLAY = "#45475a"   # overlay0, muted text / inactive
TEXT    = "#cdd6f4"   # main text — blue-tinted white like in screenshot
SUBTEXT = "#a6adc8"   # subtext0
MUTED   = "#585b70"   # comment, very muted
ACCENT  = "#89b4fa"   # blue — matches the fastfetch highlight color
GREEN   = "#a6e3a1"   # green — like the ✓ lines
YELLOW  = "#f9e2af"   # yellow — warnings
RED     = "#f38ba8"   # red — errors
TEAL    = "#94e2d5"   # teal — for variety
BORDER  = "#313244"   # 1px borders everywhere

# Fonts — SF Mono on mac, JetBrains Mono fallback, Consolas on windows
if IS_MAC:
    MONO = "SF Mono"
elif IS_WINDOWS:
    MONO = "Cascadia Code" if True else "Consolas"
else:
    MONO = "JetBrains Mono"

def f(size, bold=False, italic=False):
    weight = "bold" if bold else "normal"
    slant  = "italic" if italic else "roman"
    return (MONO, size, weight, slant)


# ── App ────────────────────────────────────────────────────────────────────────

class JBScrapeUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("jbscrape — ui wrapper")
        self.geometry("960x680")
        self.minsize(720, 500)
        self.configure(bg=BG)
        # Remove default titlebar decorations on supported platforms
        # self.overrideredirect(True)  # uncomment for fully borderless
        self._proc       = None
        self._pty_master = None
        self._stdin_pipe = None
        self._build_ui()
        self._auto_find_script()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_titlebar()
        self._build_config()
        self._build_output()
        self._build_input_row()
        self._build_statusbar()

    # ── Titlebar ──────────────────────────────────────────────────────────────

    def _build_titlebar(self):
        bar = tk.Frame(self, bg=MANTLE, height=32)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # left: name
        tk.Label(bar, text=" jbscrape", font=f(11, bold=True),
                 fg=ACCENT, bg=MANTLE).pack(side="left", padx=(8, 0))
        platform_str = "windows" if IS_WINDOWS else "macos"
        tk.Label(bar, text=f"  ·  ui wrapper  ·  {platform_str}",
                 font=f(10), fg=MUTED, bg=MANTLE).pack(side="left")

        # right: status dot
        self._dot = tk.Label(bar, text="● idle", font=f(9),
                             fg=OVERLAY, bg=MANTLE)
        self._dot.pack(side="right", padx=14)

        # bottom border
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

    # ── Config panel ──────────────────────────────────────────────────────────

    def _build_config(self):
        outer = tk.Frame(self, bg=MANTLE)
        outer.pack(fill="x")

        # ── paths block
        self._section_label(outer, "paths")

        grid = tk.Frame(outer, bg=MANTLE)
        grid.pack(fill="x", padx=14, pady=(2, 6))
        grid.columnconfigure(1, weight=1)

        self._path_row(grid, row=0, label="script",
                       var_name="_script_var", browse_cmd=self._browse)
        self._path_row(grid, row=1, label="python",
                       var_name="_python_var", browse_cmd=self._browse_python,
                       default=sys.executable)

        # ── options block
        self._section_label(outer, "options")

        opts = tk.Frame(outer, bg=MANTLE)
        opts.pack(fill="x", padx=14, pady=(2, 0))

        # row 1 — browser, sites
        r1 = tk.Frame(opts, bg=MANTLE)
        r1.pack(fill="x", pady=(0, 6))

        self._inline_label(r1, "browser")
        self._browser_var = tk.StringVar(value="chrome")
        style = ttk.Style()
        style.theme_use("default")
        style.configure("JB.TCombobox",
                        fieldbackground=CRUST, background=CRUST,
                        foreground=TEXT, selectbackground=SURFACE,
                        selectforeground=ACCENT, borderwidth=0,
                        arrowcolor=MUTED, relief="flat")
        style.map("JB.TCombobox", fieldbackground=[("readonly", CRUST)])
        cb = ttk.Combobox(r1, textvariable=self._browser_var,
                          values=["chrome", "firefox", "edge"],
                          state="readonly", width=9,
                          style="JB.TCombobox", font=f(10))
        cb.pack(side="left", ipady=3, padx=(4, 20))

        self._inline_label(r1, "sites")
        self._sites_ebay   = tk.BooleanVar(value=True)
        self._sites_swappa = tk.BooleanVar(value=True)
        self._pill_check(r1, "ebay",   self._sites_ebay,   ACCENT)
        self._pill_check(r1, "swappa", self._sites_swappa, GREEN)

        # row 2 — pages, delay, flags
        r2 = tk.Frame(opts, bg=MANTLE)
        r2.pack(fill="x", pady=(0, 6))

        self._inline_label(r2, "pages")
        self._pages_var = tk.StringVar(value="3")
        self._num_entry(r2, self._pages_var)

        self._inline_label(r2, "delay", pad_left=16)
        self._delay_var = tk.StringVar(value="2")
        self._num_entry(r2, self._delay_var)

        tk.Frame(r2, bg=MANTLE, width=20).pack(side="left")

        self._no_headless_var = tk.BooleanVar(value=False)
        self._interactive_var = tk.BooleanVar(value=False)
        self._note_var        = tk.BooleanVar(value=False)
        note_label = "--note (notepad)" if IS_WINDOWS else "--note (notes)"
        self._pill_check(r2, "--no-headless", self._no_headless_var, YELLOW)
        self._pill_check(r2, "--interactive", self._interactive_var, YELLOW)
        self._pill_check(r2, note_label,      self._note_var,        YELLOW)

        # ── toolbar
        tk.Frame(outer, bg=BORDER, height=1).pack(fill="x", pady=(6, 0))
        toolbar = tk.Frame(outer, bg=MANTLE)
        toolbar.pack(fill="x", padx=14, pady=8)

        self._run_btn = tk.Button(
            toolbar, text="▶ run",
            font=f(10, bold=True),
            fg=CRUST, bg=ACCENT,
            activeforeground=CRUST, activebackground=TEXT,
            relief="flat", cursor="hand2",
            padx=16, pady=6, bd=0,
            command=self._run,
        )
        self._run_btn.pack(side="left", padx=(0, 4))

        self._stop_btn = tk.Button(
            toolbar, text="■ stop",
            font=f(10, bold=True),
            fg=OVERLAY, bg=SURFACE,
            activeforeground=RED, activebackground=SURFACE,
            relief="flat", cursor="hand2",
            padx=12, pady=6, bd=0, state="disabled",
            command=self._stop,
        )
        self._stop_btn.pack(side="left", padx=(0, 4))

        tk.Button(toolbar, text="clear",
                  font=f(10), fg=MUTED, bg=MANTLE,
                  activeforeground=SUBTEXT, activebackground=MANTLE,
                  relief="flat", cursor="hand2",
                  padx=10, pady=6, bd=0,
                  command=self._clear).pack(side="left", padx=(0, 4))

        tk.Button(toolbar, text="open folder",
                  font=f(10), fg=MUTED, bg=MANTLE,
                  activeforeground=SUBTEXT, activebackground=MANTLE,
                  relief="flat", cursor="hand2",
                  padx=10, pady=6, bd=0,
                  command=self._open_folder).pack(side="right")

        # bottom border
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

    # ── Output ────────────────────────────────────────────────────────────────

    def _build_output(self):
        wrap = tk.Frame(self, bg=BG)
        wrap.pack(fill="both", expand=True)
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        self._out = tk.Text(
            wrap,
            font=f(10),
            bg=BG, fg=TEXT,
            insertbackground=ACCENT,
            relief="flat", bd=0,
            state="disabled",
            wrap="word",
            cursor="arrow",
            padx=16, pady=10,
            spacing1=1, spacing3=1,
        )

        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self._out.yview)
        style = ttk.Style()
        style.configure("JB.Vertical.TScrollbar",
                        background=SURFACE, troughcolor=BG,
                        bordercolor=BG, arrowcolor=OVERLAY, relief="flat")
        vsb.configure(style="JB.Vertical.TScrollbar")
        self._out.configure(yscrollcommand=vsb.set)

        self._out.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        for tag, color in [
            ("green",  GREEN),  ("yellow", YELLOW), ("red",    RED),
            ("cyan",   ACCENT), ("muted",  MUTED),  ("white",  TEXT),
            ("input",  TEAL),   ("purple", "#cba6f7"),
            ("subtext", SUBTEXT),
        ]:
            self._out.tag_configure(tag, foreground=color)

    # ── Input row ─────────────────────────────────────────────────────────────

    def _build_input_row(self):
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        row = tk.Frame(self, bg=MANTLE)
        row.pack(fill="x")

        tk.Label(row, text=" ›", font=f(12, bold=True),
                 fg=ACCENT, bg=MANTLE).pack(side="left", padx=(6, 0))

        self._input_var = tk.StringVar()
        self._input_entry = tk.Entry(
            row, textvariable=self._input_var,
            font=f(10),
            bg=MANTLE, fg=YELLOW,
            insertbackground=YELLOW,
            relief="flat", bd=0,
            highlightthickness=0,
            state="disabled",
        )
        self._input_entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(6, 6))
        self._input_entry.bind("<Return>", lambda e: self._send_input())

        self._send_btn = tk.Button(
            row, text="send",
            font=f(9),
            fg=CRUST, bg=YELLOW,
            activeforeground=CRUST, activebackground=TEXT,
            relief="flat", cursor="hand2",
            padx=10, pady=5, bd=0, state="disabled",
            command=self._send_input,
        )
        self._send_btn.pack(side="left", padx=(0, 4), pady=4)

        if not IS_WINDOWS:
            self._ctrlc_btn = tk.Button(
                row, text="ctrl+c",
                font=f(9),
                fg=OVERLAY, bg=SURFACE,
                activeforeground=RED, activebackground=SURFACE,
                relief="flat", cursor="hand2",
                padx=8, pady=5, bd=0, state="disabled",
                command=self._send_ctrlc,
            )
            self._ctrlc_btn.pack(side="left", padx=(0, 8), pady=4)
        else:
            self._ctrlc_btn = None

        tk.Label(row, text="type a choice and press enter  ",
                 font=f(8, italic=True), fg=MUTED, bg=MANTLE).pack(side="left")

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_statusbar(self):
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        bar = tk.Frame(self, bg=CRUST, height=20)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        self._status = tk.Label(bar, text="ready", font=f(8),
                                fg=MUTED, bg=CRUST)
        self._status.pack(side="left", padx=14)
        platform_str = "windows · notepad" if IS_WINDOWS else "macos · notes app"
        tk.Label(bar, text=platform_str, font=f(8),
                 fg=MUTED, bg=CRUST).pack(side="right", padx=14)

    # ── Widget helpers ────────────────────────────────────────────────────────

    def _section_label(self, parent, text):
        """Dim uppercase section header with a rule line."""
        row = tk.Frame(parent, bg=MANTLE)
        row.pack(fill="x", padx=14, pady=(10, 2))
        tk.Label(row, text=text, font=f(8),
                 fg=MUTED, bg=MANTLE).pack(side="left")
        tk.Frame(row, bg=BORDER, height=1).pack(
            side="left", fill="x", expand=True, padx=(8, 0), pady=4)

    def _inline_label(self, parent, text, pad_left=0):
        tk.Label(parent, text=text, font=f(9),
                 fg=OVERLAY, bg=MANTLE).pack(side="left", padx=(pad_left, 4))

    def _path_row(self, grid, row, label, var_name, browse_cmd, default=""):
        tk.Label(grid, text=label, font=f(9),
                 fg=OVERLAY, bg=MANTLE, width=8, anchor="w").grid(
            row=row, column=0, sticky="w", pady=(0, 4))

        var = tk.StringVar(value=default)
        setattr(self, var_name, var)

        entry_wrap = tk.Frame(grid, bg=CRUST,
                              highlightthickness=1,
                              highlightbackground=BORDER,
                              highlightcolor=ACCENT)
        entry_wrap.grid(row=row, column=1, sticky="ew", pady=(0, 4), padx=(0, 6))
        tk.Entry(entry_wrap, textvariable=var, font=f(10),
                 bg=CRUST, fg=TEXT, insertbackground=ACCENT,
                 relief="flat", bd=0
                 ).pack(fill="x", expand=True, ipady=4, padx=6)

        tk.Button(grid, text="browse", font=f(9),
                  fg=OVERLAY, bg=SURFACE,
                  activeforeground=TEXT, activebackground=SURFACE,
                  relief="flat", cursor="hand2",
                  padx=8, pady=4, bd=0,
                  command=browse_cmd).grid(row=row, column=2)

    def _num_entry(self, parent, var):
        wrap = tk.Frame(parent, bg=CRUST,
                        highlightthickness=1,
                        highlightbackground=BORDER,
                        highlightcolor=ACCENT)
        wrap.pack(side="left", padx=(4, 0))
        tk.Entry(wrap, textvariable=var, font=f(10),
                 bg=CRUST, fg=TEXT, insertbackground=ACCENT,
                 relief="flat", bd=0, width=4
                 ).pack(ipady=3, ipadx=4)

    def _pill_check(self, parent, text, var, color):
        """Tiny inline toggle that looks like a dim badge when off."""
        frame = tk.Frame(parent, bg=MANTLE, cursor="hand2")
        frame.pack(side="left", padx=(0, 12))

        dot = tk.Label(frame, font=f(9), bg=MANTLE)
        lbl = tk.Label(frame, text=text, font=f(9), bg=MANTLE)
        dot.pack(side="left", padx=(0, 4))
        lbl.pack(side="left")

        def _draw():
            if var.get():
                dot.config(text="◆", fg=color)
                lbl.config(fg=TEXT)
            else:
                dot.config(text="◇", fg=MUTED)
                lbl.config(fg=MUTED)

        def _toggle(_=None):
            var.set(not var.get())
            _draw()

        _draw()
        for w in (frame, dot, lbl):
            w.bind("<Button-1>", _toggle)

    # ── Script discovery ──────────────────────────────────────────────────────

    def _auto_find_script(self):
        if IS_WINDOWS:
            names = ["JBScrape_windows.py", "jbscrape_windows.py",
                     "JBScrape.py", "jbscrape.py"]
        else:
            names = ["JBScrape.py", "jbscrape.py",
                     "JBScrape_windows.py", "jbscrape_windows.py"]

        search_dirs = [
            os.path.join(os.path.expanduser("~"), "JBScrape"),
            os.path.join(os.path.expanduser("~"), "Downloads", "JBScrape"),
            os.path.join(os.path.expanduser("~"), "Desktop", "JBScrape"),
            os.getcwd(),
            os.path.dirname(os.path.abspath(__file__)),
        ]

        for d in search_dirs:
            for name in names:
                path = os.path.join(d, name)
                if os.path.isfile(path):
                    self._script_var.set(path)
                    self._print(f"✓  found {name}\n   {path}\n\n", "green")
                    return

        self._print(
            "⚠  script not found automatically.\n"
            "   set the path above to JBScrape.py (macos) or JBScrape_windows.py (windows).\n\n",
            "yellow",
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _browse(self):
        path = filedialog.askopenfilename(
            title="select JBScrape script",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if path:
            self._script_var.set(path)

    def _browse_python(self):
        path = filedialog.askopenfilename(title="select Python interpreter")
        if path:
            self._python_var.set(path)

    def _open_folder(self):
        script = self._script_var.get()
        folder = os.path.dirname(script) if script and os.path.exists(script) \
                 else os.path.expanduser("~")
        if IS_WINDOWS:
            subprocess.Popen(["explorer", folder])
        elif IS_MAC:
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    def _print(self, text, tag="white"):
        self._out.configure(state="normal")
        self._out.insert("end", text, tag)
        self._out.see("end")
        self._out.configure(state="disabled")

    def _clear(self):
        self._out.configure(state="normal")
        self._out.delete("1.0", "end")
        self._out.configure(state="disabled")

    def _set_status(self, msg, dot_color=None):
        self._status.configure(text=msg)
        self._dot.configure(text=f"● {msg}", fg=dot_color or OVERLAY)

    def _colorize(self, line):
        l = line.lower()
        if any(x in l for x in ["error", "✗", "failed", "exception", "traceback"]):
            return "red"
        if any(x in l for x in ["warning", "⚠", "warn"]):
            return "yellow"
        if any(x in l for x in ["found", "✓", "done", "complete", "result", "listing"]):
            return "green"
        if any(x in l for x in ["scanning", "searching", "──", "▶", "ebay", "swappa"]):
            return "cyan"
        if line.startswith("  ") or line.startswith("\t"):
            return "subtext"
        return "white"

    # ── Run / Stop ────────────────────────────────────────────────────────────

    def _run(self):
        script = self._script_var.get().strip()
        if not script:
            messagebox.showwarning("no script", "set the path to the JBScrape script.")
            return
        if not os.path.isfile(script):
            messagebox.showerror("not found", f"file not found:\n{script}")
            return

        python = self._python_var.get().strip() or sys.executable
        cmd    = [python, script, "--browser", self._browser_var.get()]

        sites = []
        if self._sites_ebay.get():   sites.append("ebay")
        if self._sites_swappa.get(): sites.append("swappa")
        if sites: cmd += ["--sites"] + sites

        pages = self._pages_var.get().strip()
        if pages and pages.isdigit(): cmd += ["--pages", pages]

        delay = self._delay_var.get().strip()
        if delay: cmd += ["--delay", delay]

        if self._no_headless_var.get():  cmd.append("--no-headless")
        if self._interactive_var.get():  cmd.append("--interactive")
        if self._note_var.get():         cmd.append("--note")

        self._clear()
        self._print(f"▶  {' '.join(cmd)}\n\n", "cyan")
        self._run_btn.configure(state="disabled", bg=SURFACE, fg=MUTED)
        self._stop_btn.configure(state="normal",  bg=RED,     fg=CRUST,
                                 activeforeground=CRUST, activebackground=RED)
        self._input_entry.configure(state="normal")
        self._send_btn.configure(state="normal")
        if self._ctrlc_btn:
            self._ctrlc_btn.configure(state="normal")
        self._input_entry.focus_set()
        self._set_status("running…", GREEN)

        threading.Thread(target=self._run_worker, args=(cmd, script), daemon=True).start()

    def _run_worker(self, cmd, script):
        cwd = os.path.dirname(script)
        if IS_WINDOWS:
            self._run_worker_windows(cmd, cwd)
        else:
            self._run_worker_pty(cmd, cwd)

    # ── macOS / Linux: PTY ────────────────────────────────────────────────────

    def _run_worker_pty(self, cmd, cwd):
        import pty
        master_fd, slave_fd = pty.openpty()
        self._pty_master = master_fd
        try:
            self._proc = subprocess.Popen(
                cmd, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
                cwd=cwd, close_fds=True,
            )
            os.close(slave_fd); slave_fd = -1

            buf = b""
            while True:
                try:
                    chunk = os.read(master_fd, 1024)
                except OSError:
                    break
                if not chunk: break
                buf += chunk
                text = buf.decode("utf-8", errors="replace")
                buf  = b""
                self.after(0, self._print, text, self._colorize(text))

            self._proc.wait()
            self._finish(self._proc.returncode)

        except FileNotFoundError as e:
            self.after(0, self._print, f"✗  could not start: {e}\n", "red")
            self.after(0, self._set_status, "error", RED)
        except Exception as e:
            self.after(0, self._print, f"✗  {e}\n", "red")
            self.after(0, self._set_status, "error", RED)
        finally:
            try: os.close(master_fd)
            except OSError: pass
            if slave_fd != -1:
                try: os.close(slave_fd)
                except OSError: pass
            self._proc       = None
            self._pty_master = None
            self.after(0, self._run_done)

    # ── Windows: pipe-based ───────────────────────────────────────────────────

    def _run_worker_windows(self, cmd, cwd):
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0,
            )
            self._stdin_pipe = self._proc.stdin

            for line in self._proc.stdout:
                self.after(0, self._print, line, self._colorize(line))

            self._proc.wait()
            self._finish(self._proc.returncode)

        except FileNotFoundError as e:
            self.after(0, self._print, f"✗  could not start: {e}\n", "red")
            self.after(0, self._set_status, "error", RED)
        except Exception as e:
            self.after(0, self._print, f"✗  {e}\n", "red")
            self.after(0, self._set_status, "error", RED)
        finally:
            self._proc        = None
            self._stdin_pipe  = None
            self.after(0, self._run_done)

    def _finish(self, rc):
        if rc == 0:
            self.after(0, self._print, "\n✓  jbscrape finished.\n", "green")
            self.after(0, self._set_status, "done", ACCENT)
        elif rc is not None and rc < 0:
            self.after(0, self._print, "\n⏹  stopped.\n", "yellow")
            self.after(0, self._set_status, "stopped", YELLOW)
        else:
            self.after(0, self._print, f"\n⚠  exited with code {rc}\n", "yellow")
            self.after(0, self._set_status, f"exited ({rc})", YELLOW)

    def _stop(self):
        if self._proc:
            try:
                self._proc.terminate()
                threading.Timer(2.0, self._force_kill).start()
            except Exception:
                pass
        self._set_status("stopping…", YELLOW)
        self._stop_btn.configure(state="disabled", bg=SURFACE, fg=OVERLAY)

    def _force_kill(self):
        if self._proc:
            try: self._proc.kill()
            except Exception: pass

    def _send_ctrlc(self):
        if self._pty_master is not None:
            try: os.write(self._pty_master, b"\x03")
            except OSError: pass

    def _send_input(self):
        text = self._input_var.get()
        self._input_var.set("")
        if not text:
            return
        if IS_WINDOWS:
            if self._stdin_pipe:
                try:
                    self._stdin_pipe.write(text + "\n")
                    self._stdin_pipe.flush()
                    self._print(f"› {text}\n", "input")
                except OSError:
                    self._print("⚠  could not send input.\n", "yellow")
        else:
            if self._pty_master is not None:
                try: os.write(self._pty_master, (text + "\n").encode())
                except OSError:
                    self._print("⚠  could not send input.\n", "yellow")

    def _run_done(self):
        self._run_btn.configure(state="normal",   bg=ACCENT,  fg=CRUST)
        self._stop_btn.configure(state="disabled", bg=SURFACE, fg=OVERLAY)
        self._input_entry.configure(state="disabled")
        self._send_btn.configure(state="disabled")
        if self._ctrlc_btn:
            self._ctrlc_btn.configure(state="disabled")


# ── Entry ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = JBScrapeUI()
    app.mainloop()
