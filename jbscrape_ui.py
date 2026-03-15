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

# ─── Colors ───────────────────────────────────────────────────────────────────

BG      = "#0d0f14"
BG2     = "#13161e"
BG3     = "#1a1e28"
ACCENT  = "#00e5ff"
ACCENT2 = "#ff4d6d"
GREEN   = "#00ff9f"
YELLOW  = "#ffd166"
TEXT    = "#e2e8f0"
MUTED   = "#64748b"
BORDER  = "#1e2535"

MONO = "SF Mono" if IS_MAC else "Consolas"

# ─── App ─────────────────────────────────────────────────────────────────────

class JBScrapeUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JBScrape UI")
        self.geometry("920x660")
        self.minsize(700, 480)
        self.configure(bg=BG)
        self._proc       = None
        self._pty_master = None   # macOS/Linux only
        self._stdin_pipe = None   # Windows only
        self._build_ui()
        self._auto_find_script()

    def _f(self, size, bold=False):
        return (MONO, size, "bold") if bold else (MONO, size)

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_config()
        self._build_statusbar()
        self._build_input_row()
        self._build_output()

    def _build_header(self):
        hdr = tk.Frame(self, bg=BG2, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        platform_label = "Windows" if IS_WINDOWS else "macOS"
        tk.Label(hdr, text="◈  JBScrape UI", font=self._f(17, True),
                 fg=ACCENT, bg=BG2).pack(side="left", padx=20, pady=10)
        tk.Label(hdr, text=f"wrapper for JBScrape  ·  {platform_label}",
                 font=self._f(10), fg=MUTED, bg=BG2).pack(side="left")
        self._dot = tk.Label(hdr, text="●  idle", font=self._f(10), fg=MUTED, bg=BG2)
        self._dot.pack(side="right", padx=20)

    def _build_config(self):
        cfg = tk.Frame(self, bg=BG2)
        cfg.pack(fill="x", padx=14, pady=(10, 0))

        # Script path
        row1 = tk.Frame(cfg, bg=BG2)
        row1.pack(fill="x", pady=(8, 4))
        tk.Label(row1, text="jbscrape.py", font=self._f(11), fg=MUTED, bg=BG2,
                 width=12, anchor="w").pack(side="left")
        self._script_var = tk.StringVar()
        tk.Entry(row1, textvariable=self._script_var, font=self._f(11),
                 bg=BG3, fg=TEXT, insertbackground=ACCENT, relief="flat", bd=0
                 ).pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))
        tk.Button(row1, text="Browse", font=self._f(10), fg=TEXT, bg=BG3,
                  relief="flat", cursor="hand2", padx=10, pady=4, bd=0,
                  command=self._browse).pack(side="left")

        # Python interpreter
        row2 = tk.Frame(cfg, bg=BG2)
        row2.pack(fill="x", pady=4)
        tk.Label(row2, text="Python", font=self._f(11), fg=MUTED, bg=BG2,
                 width=12, anchor="w").pack(side="left")
        self._python_var = tk.StringVar(value=sys.executable)
        tk.Entry(row2, textvariable=self._python_var, font=self._f(11),
                 bg=BG3, fg=TEXT, insertbackground=ACCENT, relief="flat", bd=0
                 ).pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))
        tk.Button(row2, text="Browse", font=self._f(10), fg=TEXT, bg=BG3,
                  relief="flat", cursor="hand2", padx=10, pady=4, bd=0,
                  command=self._browse_python).pack(side="left")

        # --browser row
        opts1 = tk.Frame(cfg, bg=BG2)
        opts1.pack(fill="x", pady=(6, 2))
        tk.Label(opts1, text="--browser", font=self._f(11), fg=MUTED, bg=BG2,
                 width=12, anchor="w").pack(side="left")
        self._browser_var = tk.StringVar(value="chrome")
        nb_style = ttk.Style()
        nb_style.theme_use("default")
        nb_style.configure("JB.TCombobox", fieldbackground=BG3, background=BG3,
                            foreground=TEXT, selectbackground=BG3,
                            selectforeground=ACCENT, borderwidth=0)
        ttk.Combobox(opts1, textvariable=self._browser_var,
                     values=["chrome", "firefox", "edge"],
                     state="readonly", width=12,
                     style="JB.TCombobox", font=self._f(11)
                     ).pack(side="left", ipady=4, padx=(0, 16))

        # --sites
        tk.Label(opts1, text="--sites", font=self._f(11), fg=MUTED, bg=BG2
                 ).pack(side="left", padx=(0, 6))
        self._sites_ebay   = tk.BooleanVar(value=True)
        self._sites_swappa = tk.BooleanVar(value=True)
        tk.Checkbutton(opts1, text="ebay", variable=self._sites_ebay,
                       font=self._f(11), fg=TEXT, bg=BG2, selectcolor=ACCENT,
                       activebackground=BG2, highlightthickness=0
                       ).pack(side="left", padx=(0, 4))
        tk.Checkbutton(opts1, text="swappa", variable=self._sites_swappa,
                       font=self._f(11), fg=TEXT, bg=BG2, selectcolor=ACCENT,
                       activebackground=BG2, highlightthickness=0
                       ).pack(side="left", padx=(0, 16))

        # --pages / --delay / flags row
        opts2 = tk.Frame(cfg, bg=BG2)
        opts2.pack(fill="x", pady=(2, 8))
        tk.Label(opts2, text="--pages", font=self._f(11), fg=MUTED, bg=BG2,
                 width=12, anchor="w").pack(side="left")
        self._pages_var = tk.StringVar(value="3")
        tk.Entry(opts2, textvariable=self._pages_var, font=self._f(11),
                 bg=BG3, fg=TEXT, insertbackground=ACCENT,
                 relief="flat", bd=0, width=4
                 ).pack(side="left", ipady=4, padx=(0, 16))

        tk.Label(opts2, text="--delay", font=self._f(11), fg=MUTED, bg=BG2
                 ).pack(side="left", padx=(0, 4))
        self._delay_var = tk.StringVar(value="2")
        tk.Entry(opts2, textvariable=self._delay_var, font=self._f(11),
                 bg=BG3, fg=TEXT, insertbackground=ACCENT,
                 relief="flat", bd=0, width=4
                 ).pack(side="left", ipady=4, padx=(0, 16))

        self._no_headless_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opts2, text="--no-headless", variable=self._no_headless_var,
                       font=self._f(11), fg=TEXT, bg=BG2, selectcolor=ACCENT,
                       activebackground=BG2, highlightthickness=0
                       ).pack(side="left", padx=(0, 8))

        self._interactive_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opts2, text="--interactive", variable=self._interactive_var,
                       font=self._f(11), fg=TEXT, bg=BG2, selectcolor=ACCENT,
                       activebackground=BG2, highlightthickness=0
                       ).pack(side="left", padx=(0, 8))

        note_label = "--note (Notepad)" if IS_WINDOWS else "--note (Notes app)"
        self._note_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opts2, text=note_label, variable=self._note_var,
                       font=self._f(11), fg=TEXT, bg=BG2, selectcolor=ACCENT,
                       activebackground=BG2, highlightthickness=0
                       ).pack(side="left")

        # Toolbar
        tk.Frame(cfg, bg=BORDER, height=1).pack(fill="x", pady=(0, 8))
        toolbar = tk.Frame(cfg, bg=BG2)
        toolbar.pack(fill="x", pady=(0, 10))

        self._run_btn = tk.Button(toolbar, text="▶  RUN", font=self._f(12, True),
                                  fg=BG, bg=ACCENT, relief="flat", cursor="hand2",
                                  padx=20, pady=8, bd=0, command=self._run)
        self._run_btn.pack(side="left", padx=(0, 6))

        self._stop_btn = tk.Button(toolbar, text="■  STOP", font=self._f(12, True),
                                   fg=TEXT, bg=BG3, relief="flat", cursor="hand2",
                                   padx=14, pady=8, bd=0, state="disabled",
                                   command=self._stop)
        self._stop_btn.pack(side="left", padx=(0, 6))

        tk.Button(toolbar, text="✕  Clear", font=self._f(10), fg=MUTED, bg=BG3,
                  relief="flat", cursor="hand2", padx=10, pady=8, bd=0,
                  command=self._clear).pack(side="left")

        tk.Button(toolbar, text="📂  Open folder", font=self._f(10), fg=MUTED, bg=BG3,
                  relief="flat", cursor="hand2", padx=10, pady=8, bd=0,
                  command=self._open_folder).pack(side="right")

    def _build_input_row(self):
        row = tk.Frame(self, bg=BG2)
        row.pack(fill="x", side="bottom", padx=14, pady=(0, 4))

        tk.Label(row, text="›", font=self._f(14, True),
                 fg=ACCENT, bg=BG2).pack(side="left", padx=(6, 4))

        self._input_var = tk.StringVar()
        self._input_entry = tk.Entry(row, textvariable=self._input_var,
                                     font=self._f(11), bg=BG3, fg=YELLOW,
                                     insertbackground=YELLOW, relief="flat", bd=0,
                                     state="disabled")
        self._input_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))
        self._input_entry.bind("<Return>", lambda e: self._send_input())

        self._send_btn = tk.Button(row, text="Send", font=self._f(10),
                                   fg=BG, bg=YELLOW, relief="flat", cursor="hand2",
                                   padx=12, pady=4, bd=0, state="disabled",
                                   command=self._send_input)
        self._send_btn.pack(side="left", padx=(0, 4))

        # Ctrl+C only available on macOS/Linux (PTY)
        if not IS_WINDOWS:
            self._ctrlc_btn = tk.Button(row, text="Ctrl+C", font=self._f(10),
                                        fg=TEXT, bg=ACCENT2, relief="flat", cursor="hand2",
                                        padx=10, pady=4, bd=0, state="disabled",
                                        command=self._send_ctrlc)
            self._ctrlc_btn.pack(side="left", padx=(0, 8))
        else:
            self._ctrlc_btn = None

        tk.Label(row, text="Type a menu choice and press Enter",
                 font=self._f(9), fg=MUTED, bg=BG2).pack(side="left")

    def _build_output(self):
        frame = tk.Frame(self, bg=BG)
        frame.pack(fill="both", expand=True, padx=14, pady=(8, 4))
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self._out = tk.Text(frame, font=self._f(11), bg=BG2, fg=TEXT,
                            insertbackground=ACCENT, relief="flat", bd=0,
                            state="disabled", wrap="word", cursor="arrow")
        vsb = tk.Scrollbar(frame, orient="vertical", command=self._out.yview)
        self._out.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        self._out.grid(row=0, column=0, sticky="nsew")

        for tag, fg in [("green", GREEN), ("yellow", YELLOW), ("red", ACCENT2),
                        ("cyan", ACCENT), ("muted", MUTED), ("white", TEXT),
                        ("input", YELLOW)]:
            self._out.tag_configure(tag, foreground=fg)

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=BG3, height=22)
        bar.pack(fill="x", side="bottom")
        self._status = tk.Label(bar, text="Ready.", font=self._f(10), fg=MUTED, bg=BG3)
        self._status.pack(side="left", padx=12)
        platform_str = "Windows — Notepad output" if IS_WINDOWS else "macOS — Notes app output"
        tk.Label(bar, text=platform_str, font=self._f(10), fg=MUTED, bg=BG3
                 ).pack(side="right", padx=12)

    # ── Script discovery ──────────────────────────────────────────────────────

    def _auto_find_script(self):
        # On Windows look for JBScrape_windows.py first, then fall back to JBScrape.py
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
                    self._print(f"✓  Found {name} at: {path}\n", "green")
                    return

        self._print(
            "⚠  Script not found automatically.\n"
            "   Set the path above to JBScrape.py (macOS) or JBScrape_windows.py (Windows).\n",
            "yellow"
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select JBScrape script",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if path:
            self._script_var.set(path)

    def _browse_python(self):
        path = filedialog.askopenfilename(title="Select Python interpreter")
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

    def _set_status(self, msg, dot_color=MUTED):
        self._status.configure(text=msg)
        self._dot.configure(text=f"●  {msg}", fg=dot_color)

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
            return "muted"
        return "white"

    # ── Run / Stop ────────────────────────────────────────────────────────────

    def _run(self):
        script = self._script_var.get().strip()
        if not script:
            messagebox.showwarning("No script", "Please set the path to the JBScrape script.")
            return
        if not os.path.isfile(script):
            messagebox.showerror("Not found", f"File not found:\n{script}")
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
        self._run_btn.configure(state="disabled", bg=MUTED)
        self._stop_btn.configure(state="normal", bg=ACCENT2)
        self._input_entry.configure(state="normal")
        self._send_btn.configure(state="normal")
        if self._ctrlc_btn:
            self._ctrlc_btn.configure(state="normal")
        self._input_entry.focus_set()
        self._set_status("Running…", dot_color=GREEN)

        threading.Thread(target=self._run_worker, args=(cmd, script), daemon=True).start()

    def _run_worker(self, cmd, script):
        cwd = os.path.dirname(script)
        if IS_WINDOWS:
            self._run_worker_windows(cmd, cwd)
        else:
            self._run_worker_pty(cmd, cwd)

    # ── macOS / Linux: PTY ───────────────────────────────────────────────────

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
                buf = b""
                self.after(0, self._print, text, self._colorize(text))

            self._proc.wait()
            self._finish(self._proc.returncode)

        except FileNotFoundError as e:
            self.after(0, self._print, f"✗  Could not start: {e}\n", "red")
            self.after(0, self._set_status, "Error.", ACCENT2)
        except Exception as e:
            self.after(0, self._print, f"✗  {e}\n", "red")
            self.after(0, self._set_status, "Error.", ACCENT2)
        finally:
            try: os.close(master_fd)
            except OSError: pass
            if slave_fd != -1:
                try: os.close(slave_fd)
                except OSError: pass
            self._proc = None
            self._pty_master = None
            self.after(0, self._run_done)

    # ── Windows: pipe-based ──────────────────────────────────────────────────

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
            self.after(0, self._print, f"✗  Could not start: {e}\n", "red")
            self.after(0, self._set_status, "Error.", ACCENT2)
        except Exception as e:
            self.after(0, self._print, f"✗  {e}\n", "red")
            self.after(0, self._set_status, "Error.", ACCENT2)
        finally:
            self._proc = None
            self._stdin_pipe = None
            self.after(0, self._run_done)

    def _finish(self, rc):
        if rc == 0:
            self.after(0, self._print, "\n✓  JBScrape finished.\n", "green")
            self.after(0, self._set_status, "Done.", ACCENT)
        elif rc is not None and rc < 0:
            self.after(0, self._print, "\n⏹  Stopped.\n", "yellow")
            self.after(0, self._set_status, "Stopped.", YELLOW)
        else:
            self.after(0, self._print, f"\n⚠  Exited with code {rc}\n", "yellow")
            self.after(0, self._set_status, f"Exited ({rc})", YELLOW)

    def _stop(self):
        if self._proc:
            try:
                self._proc.terminate()
                threading.Timer(2.0, self._force_kill).start()
            except Exception:
                pass
        self._set_status("Stopping…", dot_color=YELLOW)
        self._stop_btn.configure(state="disabled", bg=BG3)

    def _force_kill(self):
        if self._proc:
            try: self._proc.kill()
            except Exception: pass

    def _send_ctrlc(self):
        """Send Ctrl+C via PTY (macOS/Linux only)."""
        if self._pty_master is not None:
            try: os.write(self._pty_master, b"\x03")
            except OSError: pass

    def _send_input(self):
        text = self._input_var.get()
        self._input_var.set("")
        if not text:
            return
        if IS_WINDOWS:
            # Write to stdin pipe
            if self._stdin_pipe:
                try:
                    self._stdin_pipe.write(text + "\n")
                    self._stdin_pipe.flush()
                    self._print(f"› {text}\n", "input")
                except OSError:
                    self._print("⚠  Could not send input.\n", "yellow")
        else:
            # Write to PTY master
            if self._pty_master is not None:
                try: os.write(self._pty_master, (text + "\n").encode())
                except OSError:
                    self._print("⚠  Could not send input.\n", "yellow")

    def _run_done(self):
        self._run_btn.configure(state="normal", bg=ACCENT)
        self._stop_btn.configure(state="disabled", bg=BG3)
        self._input_entry.configure(state="disabled")
        self._send_btn.configure(state="disabled")
        if self._ctrlc_btn:
            self._ctrlc_btn.configure(state="disabled")


# ─── Entry ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = JBScrapeUI()
    app.mainloop()
