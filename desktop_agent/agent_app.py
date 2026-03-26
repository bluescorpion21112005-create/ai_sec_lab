import os
import threading
import queue
import psutil
import platform
import subprocess
import json
import time
import random
import hashlib
from datetime import datetime, timedelta
from tkinter import ttk, filedialog, messagebox, font
import customtkinter as ctk
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sqlite3
import paramiko
import numpy as np
import csv

# ============================================
# OPTIONAL DEPENDENCIES
# ============================================
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

try:
    from scanner_engine import scan_target
    SCANNER_AVAILABLE = True
except ImportError:
    SCANNER_AVAILABLE = False

try:
    from api_client import submit_scan_results
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False

try:
    from config import SERVER_URL, DEFAULT_TIMEOUT
except ImportError:
    SERVER_URL = "http://localhost:5000"
    DEFAULT_TIMEOUT = 30

# ============================================
# FUTURISTIC CYBER UI - COLOR THEME
# ============================================
CYBER_CYAN = "#00ffff"
CYBER_BLUE = "#00ccff"
CYBER_PURPLE = "#ff00ff"
CYBER_DARK = "#0a0a1f"
CYBER_DARKER = "#050510"
CYBER_GLASS = "#0a1428"
CYBER_SUCCESS = "#22c55e"
CYBER_WARNING = "#f59e0b"
CYBER_DANGER = "#ef4444"
CYBER_INFO = "#3b82f6"
CYBER_GOLD = "#ffd700"
CYBER_SILVER = "#c0c0c0"
CYBER_NEON = "#39ff14"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ============================================
# CUSTOM CYBER WIDGETS
# ============================================
class CyberButton(ctk.CTkButton):
    def __init__(self, *args, neon=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.neon = neon
        self.configure(
            height=44, corner_radius=12, border_width=2,
            border_color=CYBER_CYAN if not neon else CYBER_NEON,
            fg_color="transparent",
            hover_color=CYBER_CYAN if not neon else CYBER_NEON,
            text_color=CYBER_CYAN if not neon else CYBER_NEON,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, event):
        self.configure(fg_color=CYBER_CYAN if not self.neon else CYBER_NEON,
                       text_color=CYBER_DARK)

    def on_leave(self, event):
        self.configure(fg_color="transparent",
                       text_color=CYBER_CYAN if not self.neon else CYBER_NEON)


class CyberEntry(ctk.CTkEntry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure(
            height=44, corner_radius=12, border_width=2,
            border_color=CYBER_CYAN, fg_color=CYBER_DARK,
            text_color="white", placeholder_text_color="#4a5568",
            font=ctk.CTkFont(size=13)
        )
        self.bind("<FocusIn>", self.on_focus_in)
        self.bind("<FocusOut>", self.on_focus_out)

    def on_focus_in(self, event):
        self.configure(border_color=CYBER_PURPLE)

    def on_focus_out(self, event):
        self.configure(border_color=CYBER_CYAN)


class CyberProgressBar(ctk.CTkProgressBar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure(height=8, corner_radius=4,
                       progress_color=CYBER_CYAN, fg_color=CYBER_DARKER)
        self.set(0)


class CyberTextbox(ctk.CTkTextbox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure(
            corner_radius=14, font=ctk.CTkFont(size=12),
            fg_color=CYBER_DARK, border_width=2, border_color=CYBER_CYAN,
            text_color="#e2e8f0"
        )


class CyberFrame(ctk.CTkFrame):
    def __init__(self, *args, glass=True, **kwargs):
        super().__init__(*args, **kwargs)
        if glass:
            self.configure(corner_radius=20, fg_color=CYBER_GLASS,
                           border_width=2, border_color=CYBER_CYAN)
        else:
            self.configure(corner_radius=20, fg_color=CYBER_DARK,
                           border_width=1, border_color=CYBER_CYAN)


class CyberCard(ctk.CTkFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure(corner_radius=15, fg_color=CYBER_DARKER,
                       border_width=1, border_color=CYBER_CYAN)


# ============================================
# MAIN APPLICATION
# ============================================
class DesktopScannerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Patch TkinterDnD onto this CTk window if available
        self._dnd_available = False
        try:
            from tkinterdnd2 import TkinterDnD as _DnD
            _DnD.Tk._setup(self)
            self._dnd_available = True
        except Exception:
            pass

        self.title("⚡ NEURON SECURITY LAB - CYBER SCANNER v5.0")
        self.geometry("1800x1000")
        self.minsize(1400, 850)
        self.configure(fg_color=CYBER_DARKER)

        # Data storage
        self.last_result = None
        self.result_lines = []
        self.scan_history = []
        self.scan_queue = queue.Queue()
        self.current_scan_id = 0
        self.is_scanning = False
        self.log_lines = []
        self.api_stats = {"total": 0, "success": 0, "failed": 0, "response_time": []}
        self.notifications = []
        self.activity_log = []
        self.realtime_alerts = []

        # Users (role-based)
        self.users = [
            {"username": "admin", "password": "admin", "role": "admin"},
            {"username": "user",  "password": "user",  "role": "user"}
        ]
        self.current_user = "admin"

        # Plugins
        self.plugins = [
            {"name": "SQL Scanner",   "enabled": True},
            {"name": "XSS Detector",  "enabled": True},
            {"name": "Port Scanner",  "enabled": True},
            {"name": "Docker Manager","enabled": True},
        ]

        # Subscription
        self.subscription = {
            "plan": "Free",
            "expires": "2025-12-31",
            "features": ["Basic scans", "1 user"]
        }

        # VMs (simulation)
        self.vms = [
            {"name": "Kali Linux",  "status": "stopped", "os": "Linux"},
            {"name": "Windows 10",  "status": "running", "os": "Windows"},
        ]

        # SSH
        self.ssh_client = None
        self.ssh_connected = False

        # Docker
        self.docker_client = None
        self.docker_available = DOCKER_AVAILABLE
        if DOCKER_AVAILABLE:
            try:
                self.docker_client = docker.from_env()
            except Exception:
                self.docker_available = False

        # Scanner & API
        self.scanner_available = SCANNER_AVAILABLE
        self.api_available = API_AVAILABLE

        # Build UI
        self.build_ui()
        self.create_animations()
        self.start_system_monitor()
        self.load_scan_history()
        self.start_realtime_monitoring()
        self.bind_shortcuts()

    # ------------------------------------------------------------------
    # KEYBOARD SHORTCUTS
    # ------------------------------------------------------------------
    def bind_shortcuts(self):
        self.bind("<Control-s>", lambda e: self.start_scan_thread())
        self.bind("<Control-e>", lambda e: self.export_pdf())
        self.bind("<Control-c>", lambda e: self.copy_results())
        self.bind("<Control-l>", lambda e: self.clear_results())
        self.bind("<Control-h>", lambda e: self.show_help())
        self.bind("<Escape>",    lambda e: self.cancel_scan())
        self.bind("<F1>",        lambda e: self.show_help())
        self.bind("<F5>",        lambda e: self.refresh_all())

    # ------------------------------------------------------------------
    # ANIMATIONS
    # ------------------------------------------------------------------
    def create_animations(self):
        self.animate_glow()

    def animate_glow(self):
        current_time = datetime.now().strftime("%H:%M:%S")
        self.title(f"⚡ NEURON SECURITY LAB - CYBER SCANNER v5.0 [ {current_time} ]")
        self.after(1000, self.animate_glow)

    # ------------------------------------------------------------------
    # SYSTEM MONITOR
    # ------------------------------------------------------------------
    def start_system_monitor(self):
        def monitor():
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            if hasattr(self, 'cpu_label'):
                self.cpu_label.configure(text=f"⚡ CPU: {cpu}%")
                self.ram_label.configure(text=f"💾 RAM: {ram}%")
                self.cpu_label.configure(
                    text_color=CYBER_DANGER if cpu > 80 else CYBER_WARNING if cpu > 60 else CYBER_SUCCESS)
                self.ram_label.configure(
                    text_color=CYBER_DANGER if ram > 80 else CYBER_WARNING if ram > 60 else CYBER_SUCCESS)
            self.update_system_health()
            self.after(2000, monitor)
        self.after(1000, monitor)

    # ------------------------------------------------------------------
    # REAL-TIME ALERTS
    # ------------------------------------------------------------------
    def start_realtime_monitoring(self):
        def monitor():
            if random.random() < 0.05:
                threats = [
                    "Port scan detected from 192.168.1.100",
                    "Multiple failed login attempts",
                    "Suspicious packet pattern detected",
                    "Potential SQL injection attempt",
                    "XSS payload detected in traffic",
                    "Brute force attack detected",
                    "Unusual outbound traffic"
                ]
                self.add_realtime_alert(random.choice(threats))
            self.after(30000, monitor)
        self.after(5000, monitor)

    def add_realtime_alert(self, message):
        severity = random.choice(["low", "medium", "high", "critical"])
        self.realtime_alerts.insert(0, {
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": message,
            "severity": severity
        })
        if len(self.realtime_alerts) > 100:
            self.realtime_alerts = self.realtime_alerts[:100]
        if hasattr(self, 'alerts_box'):
            self.update_alerts_display()
        self.add_notification("Security Alert", message, severity)
        self.add_log("WARNING", f"Real-time alert: {message}")

    def update_alerts_display(self):
        if not hasattr(self, 'alerts_box'):
            return
        self.alerts_box.configure(state="normal")
        self.alerts_box.delete("1.0", "end")
        for alert in self.realtime_alerts[:50]:
            self.alerts_box.insert("end", f"🚨 [{alert['time']}] ", ("time",))
            self.alerts_box.insert("end", f"{alert['message']}\n", ("alert",))
        self.alerts_box.tag_config("time",  foreground=CYBER_INFO)
        self.alerts_box.tag_config("alert", foreground=CYBER_WARNING)
        self.alerts_box.configure(state="disabled")

    # ------------------------------------------------------------------
    # SCAN HISTORY
    # ------------------------------------------------------------------
    def load_scan_history(self):
        if os.path.exists("scan_history_v5.json"):
            try:
                with open("scan_history_v5.json", 'r') as f:
                    self.scan_history = json.load(f)
                    self.update_history_display()
            except Exception:
                pass

    def save_scan_history(self):
        try:
            with open("scan_history_v5.json", 'w') as f:
                json.dump(self.scan_history[-100:], f)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # NOTIFICATIONS
    # ------------------------------------------------------------------
    def add_notification(self, title, message, level="info"):
        self.notifications.insert(0, {
            "title": title, "message": message,
            "level": level,
            "time": datetime.now().strftime("%H:%M:%S"),
            "read": False
        })
        if len(self.notifications) > 100:
            self.notifications = self.notifications[:100]
        self.update_notification_center()
        if level == "critical":
            messagebox.showerror(title, message)
        elif level == "warning":
            messagebox.showwarning(title, message)

    def update_notification_center(self):
        if not hasattr(self, 'notification_box'):
            return
        self.notification_box.configure(state="normal")
        self.notification_box.delete("1.0", "end")
        for notif in self.notifications[:30]:
            color = (CYBER_DANGER  if notif["level"] == "critical" else
                     CYBER_WARNING if notif["level"] == "warning"  else
                     CYBER_SUCCESS if notif["level"] == "success"  else CYBER_INFO)
            status = "🔴" if not notif["read"] else "⚪"
            self.notification_box.insert("end", f"{status} [{notif['time']}] ", ("time",))
            self.notification_box.insert("end", f"{notif['title']}\n", ("title",))
            self.notification_box.insert("end", f"   📝 {notif['message']}\n\n", ("message",))
        self.notification_box.tag_config("time",    foreground=CYBER_INFO)
        self.notification_box.tag_config("title",   foreground=CYBER_CYAN,
                                         font=("Consolas", 11, "bold"))
        self.notification_box.tag_config("message", foreground="#aaa")
        self.notification_box.configure(state="disabled")

    # ------------------------------------------------------------------
    # ACTIVITY LOG
    # ------------------------------------------------------------------
    def add_activity(self, action, details):
        self.activity_log.insert(0, {
            "time":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action":  action,
            "details": details
        })
        if len(self.activity_log) > 200:
            self.activity_log = self.activity_log[:200]
        self.update_activity_timeline()

    def update_activity_timeline(self):
        if not hasattr(self, 'activity_box'):
            return
        self.activity_box.configure(state="normal")
        self.activity_box.delete("1.0", "end")
        for act in self.activity_log[:50]:
            self.activity_box.insert("end", f"🕒 {act['time']}\n",    ("time",))
            self.activity_box.insert("end", f"   ⚡ {act['action']}\n", ("action",))
            self.activity_box.insert("end", f"   📝 {act['details']}\n\n", ("details",))
        self.activity_box.tag_config("time",    foreground=CYBER_INFO)
        self.activity_box.tag_config("action",  foreground=CYBER_CYAN)
        self.activity_box.tag_config("details", foreground="#aaa")
        self.activity_box.configure(state="disabled")

    # ------------------------------------------------------------------
    # LOGGING
    # ------------------------------------------------------------------
    def add_log(self, level, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level.upper():7}] {message}"
        self.log_lines.insert(0, log_entry)
        if len(self.log_lines) > 1000:
            self.log_lines = self.log_lines[:1000]
        self.update_log_viewer()

    def update_log_viewer(self):
        if not hasattr(self, 'log_box'):
            return
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        for log in self.log_lines[:200]:
            color = (CYBER_DANGER  if "[ERROR]"   in log else
                     CYBER_WARNING if "[WARNING]" in log else
                     CYBER_SUCCESS if "[SUCCESS]" in log else
                     CYBER_INFO    if "[INFO]"    in log else "#aaa")
            self.log_box.insert("end", log + "\n", ("log",))
            self.log_box.tag_config("log", foreground=color)
        self.log_box.configure(state="disabled")
        self.log_box.see("end")

    # ------------------------------------------------------------------
    # API STATS
    # ------------------------------------------------------------------
    def update_api_stats(self, success=True, response_time=0):
        self.api_stats["total"] += 1
        if success:
            self.api_stats["success"] += 1
        else:
            self.api_stats["failed"] += 1
        if response_time > 0:
            self.api_stats["response_time"].append(response_time)
            if len(self.api_stats["response_time"]) > 100:
                self.api_stats["response_time"] = self.api_stats["response_time"][-100:]
        if hasattr(self, 'api_total_label'):
            self.api_total_label.configure(text=f"📊 Total: {self.api_stats['total']}")
            self.api_success_label.configure(text=f"✅ Success: {self.api_stats['success']}")
            self.api_failed_label.configure(text=f"❌ Failed: {self.api_stats['failed']}")
            if self.api_stats["response_time"]:
                avg = sum(self.api_stats["response_time"]) / len(self.api_stats["response_time"])
                self.api_avg_label.configure(text=f"⏱️ Avg: {avg:.0f}ms")

    # ==================================================================
    # UI CONSTRUCTION
    # ==================================================================
    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.build_header()
        self.build_main_content()

    # ------------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------------
    def build_header(self):
        header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=CYBER_GLASS, height=100)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_propagate(False)
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=0)
        header_frame.grid_columnconfigure(2, weight=0)

        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=30, pady=15, sticky="w")
        ctk.CTkLabel(title_frame, text="NEURON SECURITY",
                     font=ctk.CTkFont(size=28, weight="bold"),
                     text_color=CYBER_CYAN).pack(side="left")
        ctk.CTkLabel(title_frame, text=" v5.0 | Advanced Cyber Defense Platform",
                     font=ctk.CTkFont(size=12), text_color="#888").pack(side="left", padx=(15, 0))

        monitor_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        monitor_frame.grid(row=0, column=1, padx=20, pady=15)
        self.cpu_label = ctk.CTkLabel(monitor_frame, text="⚡ CPU: 0%",
                                      font=ctk.CTkFont(size=12, weight="bold"))
        self.cpu_label.pack(side="left", padx=10)
        self.ram_label = ctk.CTkLabel(monitor_frame, text="💾 RAM: 0%",
                                      font=ctk.CTkFont(size=12, weight="bold"))
        self.ram_label.pack(side="left", padx=10)

        status_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        status_frame.grid(row=0, column=2, padx=30, pady=15, sticky="e")
        self.status_indicator = ctk.CTkFrame(status_frame, width=14, height=14,
                                             corner_radius=7, fg_color=CYBER_SUCCESS)
        self.status_indicator.pack(side="left", padx=(0, 10))
        self.status_text = ctk.CTkLabel(status_frame, text="SYSTEM ACTIVE",
                                        font=ctk.CTkFont(size=12, weight="bold"),
                                        text_color=CYBER_SUCCESS)
        self.status_text.pack(side="left")

    # ------------------------------------------------------------------
    # MAIN CONTENT (notebook)
    # ------------------------------------------------------------------
    def build_main_content(self):
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        self.notebook = ctk.CTkTabview(content_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        # configure after adding a dummy tab (avoids CTk bug)
        self.notebook.add("_dummy")
        self.notebook.configure(corner_radius=14, border_width=2, border_color=CYBER_CYAN)
        try:
            self.notebook._segmented_button.configure(
                selected_color=CYBER_CYAN, selected_hover_color=CYBER_BLUE,
                unselected_color=CYBER_DARK, unselected_hover_color=CYBER_GLASS,
                text_color=CYBER_CYAN)
        except Exception:
            pass
        self.notebook.delete("_dummy")

        tabs = [
            ("🎯 Scanner",      self.build_scan_tab),
            ("📊 Dashboard",    self.build_dashboard_tab),
            ("📜 Logs",         self.build_logs_tab),
            ("🌐 Network",      self.build_network_tab),
            ("💾 Database",     self.build_database_tab),
            ("📁 Files",        self.build_file_tab),
            ("⚙️ Settings",     self.build_settings_tab),
            ("🎮 Terminal",     self.build_terminal_tab),
            ("🐳 Docker",       self.build_docker_tab),
            ("🤖 AI",           self.build_ai_tab),
            ("🗺️ Threat Map",  self.build_threat_map_tab),
            ("📡 Traffic",      self.build_traffic_tab),
            ("📋 History",      self.build_history_tab),
            ("🔔 Alerts",       self.build_alerts_tab),
            ("⏱️ Activity",    self.build_activity_tab),
            ("💻 System",       self.build_system_tab),
            ("📊 API Stats",    self.build_api_tab),
            ("👥 Users",        self.build_user_management_tab),
            ("💳 Subscription", self.build_subscription_tab),
            ("🔌 Plugins",      self.build_plugins_tab),
            ("🖥️ VMs",         self.build_vm_manager_tab),
        ]
        for name, builder in tabs:
            self.notebook.add(name)
            builder()

        # New-window button placed over header area
        self.new_window_btn = CyberButton(self, text="🪟 New Window",
                                          command=self.open_new_window, height=30)
        self.new_window_btn.place(relx=0.99, rely=0.005, anchor="ne")

    # ==================================================================
    # TAB BUILDERS
    # ==================================================================

    # ---- SCANNER TAB ------------------------------------------------
    def build_scan_tab(self):
        tab = self.notebook.tab("🎯 Scanner")
        tab.grid_columnconfigure(0, weight=0)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        left_panel = CyberFrame(tab, width=450)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        left_panel.grid_propagate(False)
        left_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left_panel, text="🔧 SCAN CONFIGURATION",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=CYBER_CYAN).grid(row=0, column=0, padx=25, pady=(25, 15), sticky="w")
        ctk.CTkFrame(left_panel, height=2, fg_color=CYBER_CYAN).grid(
            row=1, column=0, sticky="ew", padx=25, pady=(0, 20))

        ctk.CTkLabel(left_panel, text="🎯 TARGET URL",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=CYBER_INFO).grid(row=2, column=0, padx=25, pady=(0, 8), sticky="w")
        self.url_entry = CyberEntry(left_panel, placeholder_text="https://example.com")
        self.url_entry.grid(row=3, column=0, padx=25, pady=(0, 20), sticky="ew")

        ctk.CTkLabel(left_panel, text="🔑 API TOKEN",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=CYBER_INFO).grid(row=4, column=0, padx=25, pady=(0, 8), sticky="w")
        token_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        token_frame.grid(row=5, column=0, padx=25, pady=(0, 20), sticky="ew")
        token_frame.grid_columnconfigure(0, weight=1)
        self.token_entry = CyberEntry(token_frame, placeholder_text="Your API Token", show="*")
        self.token_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.token_visible = False
        self.toggle_token_btn = CyberButton(token_frame, text="👁️", width=50,
                                            command=self.toggle_token_visibility)
        self.toggle_token_btn.grid(row=0, column=1)

        ctk.CTkLabel(left_panel, text="⚙️ SCAN OPTIONS",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=CYBER_INFO).grid(row=6, column=0, padx=25, pady=(0, 8), sticky="w")
        self.deep_scan_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(left_panel, text="Deep Scan (Full Vulnerability Assessment)",
                        variable=self.deep_scan_var,
                        fg_color=CYBER_CYAN, hover_color=CYBER_BLUE).grid(
            row=7, column=0, padx=25, pady=5, sticky="w")
        self.port_scan_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(left_panel, text="Port Scanning",
                        variable=self.port_scan_var,
                        fg_color=CYBER_CYAN, hover_color=CYBER_BLUE).grid(
            row=8, column=0, padx=25, pady=5, sticky="w")

        self.scan_button = CyberButton(left_panel, text="🚀 START LOCAL SCAN",
                                       command=self.start_scan_thread, neon=True)
        self.scan_button.grid(row=9, column=0, padx=25, pady=(20, 10), sticky="ew")
        self.cloud_button = CyberButton(left_panel, text="☁️ SCAN + CLOUD SYNC",
                                        command=self.send_scan_thread)
        self.cloud_button.grid(row=10, column=0, padx=25, pady=10, sticky="ew")
        self.remote_scan_btn = CyberButton(left_panel, text="🌐 REMOTE SCAN",
                                           command=self.start_remote_scan)
        self.remote_scan_btn.grid(row=11, column=0, padx=25, pady=10, sticky="ew")

        ctk.CTkLabel(left_panel, text="📊 SCAN PROGRESS",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=CYBER_INFO).grid(row=12, column=0, padx=25, pady=(20, 8), sticky="w")
        self.progress = CyberProgressBar(left_panel)
        self.progress.grid(row=13, column=0, padx=25, pady=(0, 15), sticky="ew")
        self.status_label = ctk.CTkLabel(left_panel, text="✅ SYSTEM READY",
                                         font=ctk.CTkFont(size=12, weight="bold"),
                                         text_color=CYBER_SUCCESS)
        self.status_label.grid(row=14, column=0, padx=25, pady=(0, 25), sticky="w")

        right_panel = CyberFrame(tab)
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.grid_rowconfigure(2, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right_panel, text="📊 SCAN RESULTS",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=CYBER_CYAN).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.summary_label = ctk.CTkLabel(right_panel, text="🔍 Vulnerabilities: 0",
                                          font=ctk.CTkFont(size=12), text_color="#aaa")
        self.summary_label.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")
        self.result_box = CyberTextbox(right_panel, font=ctk.CTkFont(family="Consolas", size=11))
        self.result_box.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 15))
        self.insert_cyber_header()

        export_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        export_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        for i in range(4):
            export_frame.grid_columnconfigure(i, weight=1)
        self.copy_btn = CyberButton(export_frame, text="📋 COPY",   height=38, command=self.copy_results)
        self.copy_btn.grid(row=0, column=0, padx=5, sticky="ew")
        self.pdf_btn  = CyberButton(export_frame, text="📄 PDF",    height=38, command=self.export_pdf)
        self.pdf_btn.grid(row=0, column=1, padx=5, sticky="ew")
        self.csv_btn  = CyberButton(export_frame, text="📊 CSV",    height=38, command=self.export_csv)
        self.csv_btn.grid(row=0, column=2, padx=5, sticky="ew")
        self.clear_btn = CyberButton(export_frame, text="🗑️ CLEAR", height=38,
                                     border_color=CYBER_DANGER, text_color=CYBER_DANGER,
                                     command=self.clear_results)
        self.clear_btn.grid(row=0, column=3, padx=5, sticky="ew")

    # ---- DASHBOARD TAB ----------------------------------------------
    def build_dashboard_tab(self):
        tab = self.notebook.tab("📊 Dashboard")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        cards_frame = ctk.CTkFrame(tab, fg_color="transparent")
        cards_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=20)
        for i in range(4):
            cards_frame.grid_columnconfigure(i, weight=1)

        stats = [("Total Scans","0",CYBER_CYAN),("Vulnerabilities","0",CYBER_DANGER),
                 ("Success Rate","100%",CYBER_SUCCESS),("API Calls","0",CYBER_INFO)]
        self.stats_labels = []
        for i,(title,value,color) in enumerate(stats):
            card = CyberCard(cards_frame)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12), text_color="#aaa").pack(pady=(15,5))
            lbl = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=28, weight="bold"), text_color=color)
            lbl.pack(pady=5)
            self.stats_labels.append(lbl)

        chart_frame = CyberFrame(tab)
        chart_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=20, pady=10)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
        fig.patch.set_facecolor(CYBER_DARK)
        ax1.set_facecolor(CYBER_GLASS); ax2.set_facecolor(CYBER_GLASS)
        ax1.bar(['SQLi','XSS','CSRF','SSRF','RCE'], [15,12,8,5,3], color=CYBER_CYAN, alpha=0.7)
        ax1.set_title("Vulnerabilities by Type", color=CYBER_CYAN); ax1.tick_params(colors="#aaa")
        ax2.pie([35,30,20,15], labels=['Critical','High','Medium','Low'],
                colors=[CYBER_DANGER,CYBER_WARNING,CYBER_INFO,"#6b7280"],
                autopct='%1.1f%%', textprops={'color':'white'})
        ax2.set_title("Risk Distribution", color=CYBER_CYAN)
        self.chart_canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        self.chart_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        threat_frame = CyberFrame(tab)
        threat_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        ctk.CTkLabel(threat_frame, text="⚠️ THREAT LEVEL INDICATOR",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=CYBER_CYAN).pack(pady=10)
        self.threat_meter = ctk.CTkProgressBar(threat_frame, height=25, corner_radius=12,
                                               progress_color=CYBER_SUCCESS)
        self.threat_meter.pack(fill="x", padx=20, pady=10)
        self.threat_meter.set(0.15)
        self.threat_label = ctk.CTkLabel(threat_frame, text="🟢 LOW RISK",
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         text_color=CYBER_SUCCESS)
        self.threat_label.pack(pady=5)

        resource_frame = CyberFrame(tab)
        resource_frame.grid(row=2, column=1, sticky="nsew", padx=20, pady=10)
        ctk.CTkLabel(resource_frame, text="💻 SYSTEM RESOURCES",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=CYBER_CYAN).pack(pady=10)
        self.cpu_bar = ctk.CTkProgressBar(resource_frame, height=12, corner_radius=6,
                                          progress_color=CYBER_INFO)
        self.cpu_bar.pack(fill="x", padx=20, pady=5)
        self.cpu_label_dash = ctk.CTkLabel(resource_frame, text="CPU: 0%",
                                           font=ctk.CTkFont(size=11))
        self.cpu_label_dash.pack()
        self.ram_bar = ctk.CTkProgressBar(resource_frame, height=12, corner_radius=6,
                                          progress_color=CYBER_INFO)
        self.ram_bar.pack(fill="x", padx=20, pady=5)
        self.ram_label_dash = ctk.CTkLabel(resource_frame, text="RAM: 0%",
                                           font=ctk.CTkFont(size=11))
        self.ram_label_dash.pack()
        self.disk_bar = ctk.CTkProgressBar(resource_frame, height=12, corner_radius=6,
                                           progress_color=CYBER_INFO)
        self.disk_bar.pack(fill="x", padx=20, pady=5)
        self.disk_label = ctk.CTkLabel(resource_frame, text="DISK: 0%",
                                       font=ctk.CTkFont(size=11))
        self.disk_label.pack()

    # ---- LOGS TAB ---------------------------------------------------
    def build_logs_tab(self):
        tab = self.notebook.tab("📜 Logs")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        self.log_box = CyberTextbox(tab, font=ctk.CTkFont(family="Consolas", size=11))
        self.log_box.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        sf = ctk.CTkFrame(tab, fg_color="transparent")
        sf.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        sf.grid_columnconfigure(0, weight=1)
        self.search_entry = CyberEntry(sf, placeholder_text="🔍 Search logs...")
        self.search_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        CyberButton(sf, text="SEARCH", width=100, command=self.search_logs).grid(row=0, column=1)
        CyberButton(sf, text="CLEAR",  width=100,
                    command=lambda: self.search_entry.delete(0, 'end')).grid(row=0, column=2, padx=(10,0))

    # ---- NETWORK TAB ------------------------------------------------
    def build_network_tab(self):
        tab = self.notebook.tab("🌐 Network")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        ssh_frame = CyberFrame(tab)
        ssh_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        for i in range(4):
            ssh_frame.grid_columnconfigure(i, weight=1 if i != 1 else 0)
        ctk.CTkLabel(ssh_frame, text="🔌 SSH CLIENT",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=CYBER_CYAN).grid(row=0, column=0, columnspan=4,
                                                  padx=20, pady=10, sticky="w")
        self.ssh_host = CyberEntry(ssh_frame, placeholder_text="Host")
        self.ssh_host.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.ssh_port = CyberEntry(ssh_frame, placeholder_text="Port", width=80)
        self.ssh_port.insert(0, "22")
        self.ssh_port.grid(row=1, column=1, padx=10, pady=5)
        self.ssh_user = CyberEntry(ssh_frame, placeholder_text="Username")
        self.ssh_user.grid(row=1, column=2, padx=10, pady=5, sticky="ew")
        self.ssh_pass = CyberEntry(ssh_frame, placeholder_text="Password", show="*")
        self.ssh_pass.grid(row=1, column=3, padx=10, pady=5, sticky="ew")
        self.ssh_connect_btn = CyberButton(ssh_frame, text="CONNECT",
                                           command=self.connect_ssh)
        self.ssh_connect_btn.grid(row=2, column=0, columnspan=4, padx=20, pady=10, sticky="ew")

        self.terminal_box = CyberTextbox(tab, font=ctk.CTkFont(family="Consolas", size=11))
        self.terminal_box.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.terminal_box.insert("1.0", "⚡ SSH Terminal - Ready for connection...\n")

        cf = ctk.CTkFrame(tab, fg_color="transparent")
        cf.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        cf.grid_columnconfigure(0, weight=1)
        self.cmd_entry = CyberEntry(cf, placeholder_text="Enter command...")
        self.cmd_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.cmd_entry.bind("<Return>", lambda e: self.execute_ssh_command())
        CyberButton(cf, text="EXECUTE", width=100,
                    command=self.execute_ssh_command).grid(row=0, column=1)

    # ---- DATABASE TAB -----------------------------------------------
    def build_database_tab(self):
        tab = self.notebook.tab("💾 Database")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(1, weight=1)

        conn_frame = CyberFrame(tab)
        conn_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=20)
        conn_frame.grid_columnconfigure(0, weight=1)
        self.db_path_entry = CyberEntry(conn_frame, placeholder_text="Database path (siteguard.db)")
        self.db_path_entry.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        CyberButton(conn_frame, text="CONNECT", width=100,
                    command=self.connect_database).grid(row=0, column=1, padx=10, pady=10)

        tables_frame = CyberFrame(tab, width=250)
        tables_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        ctk.CTkLabel(tables_frame, text="📋 TABLES",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=CYBER_CYAN).pack(pady=10)
        self.tables_list = ctk.CTkTextbox(tables_frame, height=200, width=200, fg_color=CYBER_DARK)
        self.tables_list.pack(padx=10, pady=10, fill="both", expand=True)

        self.data_box = CyberTextbox(tab, font=ctk.CTkFont(family="Consolas", size=11))
        self.data_box.grid(row=1, column=1, sticky="nsew", padx=(0, 20), pady=(0, 20))
        self.data_box.insert("1.0", "📊 Database Viewer\n\nConnect to view tables.\n")

    # ---- FILES TAB --------------------------------------------------
    def build_file_tab(self):
        tab = self.notebook.tab("📁 Files")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=0)
        tab.grid_columnconfigure(1, weight=1)

        left_frame = CyberFrame(tab, width=350)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        left_frame.grid_propagate(False)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(left_frame, text="💿 DRIVE",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=CYBER_CYAN).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        self.drive_combo = ttk.Combobox(left_frame, values=self.get_drives(),
                                        state="readonly", width=30)
        self.drive_combo.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.drive_combo.bind("<<ComboboxSelected>>", self.on_drive_select)

        # Drag & Drop area (graceful fallback if tkinterdnd2 not available)
        ctk.CTkLabel(left_frame, text="📂 Drag & Drop File Here",
                     font=ctk.CTkFont(size=12),
                     text_color=CYBER_CYAN).grid(row=2, column=0, padx=10, pady=10)
        self.drop_area = CyberTextbox(left_frame, height=60)
        self.drop_area.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        self.drop_area.insert("1.0", "Drop file to scan...")
        if self._dnd_available:
            try:
                from tkinterdnd2 import DND_FILES
                self.drop_area.drop_target_register(DND_FILES)
                self.drop_area.dnd_bind('<<Drop>>', self.on_file_drop)
            except Exception:
                pass

        tree_wrapper = ctk.CTkFrame(left_frame, fg_color="transparent")
        tree_wrapper.grid(row=4, column=0, sticky="nsew", padx=10, pady=10)
        self.file_tree = ttk.Treeview(tree_wrapper, selectmode="browse", height=20)
        sb = ttk.Scrollbar(tree_wrapper, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=sb.set)
        self.file_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.file_tree.bind("<<TreeviewSelect>>", self.on_file_select)
        self.file_tree.bind("<<TreeviewOpen>>",   self._on_tree_expand)

        right_frame = CyberFrame(tab)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20)
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(right_frame, text="📄 FILE CONTENT",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=CYBER_CYAN).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.file_content = CyberTextbox(right_frame, font=ctk.CTkFont(family="Consolas", size=11))
        self.file_content.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.file_status = ctk.CTkLabel(right_frame, text="Ready",
                                        font=ctk.CTkFont(size=10), text_color="#aaa")
        self.file_status.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        drives = self.get_drives()
        if drives:
            self.drive_combo.set(drives[0])
            self.load_file_system(drives[0])

    # ---- SETTINGS TAB -----------------------------------------------
    def build_settings_tab(self):
        tab = self.notebook.tab("⚙️ Settings")
        tab.grid_columnconfigure(0, weight=1)

        sf = CyberFrame(tab)
        sf.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        sf.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(sf, text="🎨 THEME", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=CYBER_CYAN).grid(row=0, column=0, padx=20, pady=(20,10), sticky="w")
        self.theme_var = ctk.StringVar(value="dark")
        ctk.CTkRadioButton(sf, text="Dark Mode",  variable=self.theme_var, value="dark",
                           command=self.toggle_theme).grid(row=1, column=0, padx=20, pady=5, sticky="w")
        ctk.CTkRadioButton(sf, text="Light Mode", variable=self.theme_var, value="light",
                           command=self.toggle_theme).grid(row=2, column=0, padx=20, pady=5, sticky="w")

        ctk.CTkLabel(sf, text="🔍 SCAN SETTINGS", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=CYBER_CYAN).grid(row=3, column=0, padx=20, pady=(20,10), sticky="w")
        self.timeout_var = ctk.StringVar(value="30")
        tf = ctk.CTkFrame(sf, fg_color="transparent")
        tf.grid(row=4, column=0, padx=20, pady=5, sticky="w")
        ctk.CTkLabel(tf, text="Timeout (seconds):").pack(side="left")
        CyberEntry(tf, width=80, textvariable=self.timeout_var).pack(side="left", padx=(10,0))

        ctk.CTkLabel(sf, text="⌨️ KEYBOARD SHORTCUTS",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=CYBER_CYAN).grid(row=5, column=0, padx=20, pady=(20,10), sticky="w")
        kb = CyberTextbox(sf, height=150)
        kb.grid(row=6, column=0, padx=20, pady=10, sticky="ew")
        kb.insert("1.0", "  Ctrl+S  Start Scan\n  Ctrl+E  Export PDF\n  Ctrl+C  Copy Results\n"
                  "  Ctrl+L  Clear Results\n  Ctrl+H  Show Help\n  F1      Help\n"
                  "  F5      Refresh All\n  Esc     Cancel Scan")
        kb.configure(state="disabled")

    # ---- TERMINAL TAB -----------------------------------------------
    def build_terminal_tab(self):
        tab = self.notebook.tab("🎮 Terminal")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        self.local_terminal = CyberTextbox(tab, font=ctk.CTkFont(family="Consolas", size=11))
        self.local_terminal.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.local_terminal.insert("1.0", "💻 Local Terminal\nType commands below...\n\n")
        cf = ctk.CTkFrame(tab, fg_color="transparent")
        cf.grid(row=1, column=0, sticky="ew", padx=20, pady=(0,20))
        cf.grid_columnconfigure(0, weight=1)
        self.term_input = CyberEntry(cf, placeholder_text="$ Enter command...")
        self.term_input.grid(row=0, column=0, padx=(0,10), sticky="ew")
        self.term_input.bind("<Return>", lambda e: self.execute_local_command())
        CyberButton(cf, text="RUN", width=100, command=self.execute_local_command).grid(row=0, column=1)

    # ---- DOCKER TAB -------------------------------------------------
    def build_docker_tab(self):
        tab = self.notebook.tab("🐳 Docker")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        if self.docker_available:
            self.docker_box = CyberTextbox(tab, font=ctk.CTkFont(family="Consolas", size=11))
            self.docker_box.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
            self.docker_box.insert("1.0", "🐳 Docker Manager\n\nLoading containers...\n")
            self.load_docker_containers()
        else:
            ef = CyberFrame(tab)
            ef.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
            ctk.CTkLabel(ef, text="❌ Docker not available\n\npip install docker",
                         text_color=CYBER_DANGER, font=ctk.CTkFont(size=14)).pack(expand=True)

    # ---- AI TAB -----------------------------------------------------
    def build_ai_tab(self):
        tab = self.notebook.tab("🤖 AI")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        self.ai_box = CyberTextbox(tab, font=ctk.CTkFont(family="Consolas", size=11))
        self.ai_box.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.ai_box.insert("1.0", "🤖 NEURON AI Security Assistant\n\n"
                           "Ask about:\n• SQL Injection\n• XSS\n• Port Scanning\n"
                           "• Scan configuration\n\n")
        inf = ctk.CTkFrame(tab, fg_color="transparent")
        inf.grid(row=1, column=0, sticky="ew", padx=20, pady=(0,20))
        inf.grid_columnconfigure(0, weight=1)
        self.ai_input = CyberEntry(inf, placeholder_text="Ask AI assistant...")
        self.ai_input.grid(row=0, column=0, padx=(0,10), sticky="ew")
        self.ai_input.bind("<Return>", lambda e: self.process_ai_query())
        CyberButton(inf, text="ASK", width=100, neon=True,
                    command=self.process_ai_query).grid(row=0, column=1)

    # ---- THREAT MAP TAB ---------------------------------------------
    def build_threat_map_tab(self):
        tab = self.notebook.tab("🗺️ Threat Map")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        mf = CyberFrame(tab)
        mf.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor(CYBER_DARK)
        ax.set_facecolor(CYBER_GLASS)
        countries = ['USA','China','Russia','UK','Germany','France','Japan','Brazil','India','Canada']
        attacks  = [2450,1980,1760,1540,1380,1290,1120,980,890,760]
        colors   = [CYBER_DANGER if x>1500 else CYBER_WARNING if x>1000 else CYBER_INFO for x in attacks]
        ax.bar(countries, attacks, color=colors, alpha=0.8, edgecolor=CYBER_CYAN, linewidth=1)
        ax.set_title("Global Threat Distribution", color=CYBER_CYAN, fontsize=14)
        ax.set_xlabel("Country", color="#aaa"); ax.set_ylabel("Attack Count", color="#aaa")
        ax.tick_params(colors="#aaa"); ax.grid(True, alpha=0.2, color=CYBER_CYAN)
        FigureCanvasTkAgg(fig, master=mf).get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    # ---- TRAFFIC TAB ------------------------------------------------
    def build_traffic_tab(self):
        tab = self.notebook.tab("📡 Traffic")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        self.traffic_frame = CyberFrame(tab)
        self.traffic_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor(CYBER_DARK); ax.set_facecolor(CYBER_GLASS)
        self.traffic_line, = ax.plot([], [], color=CYBER_CYAN, linewidth=2)
        ax.set_title("Real-time Network Traffic", color=CYBER_CYAN, fontsize=14)
        ax.set_xlabel("Time (s)", color="#aaa"); ax.set_ylabel("Packets/sec", color="#aaa")
        ax.tick_params(colors="#aaa"); ax.grid(True, alpha=0.2, color=CYBER_CYAN)
        self.traffic_canvas = FigureCanvasTkAgg(fig, master=self.traffic_frame)
        self.traffic_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        self.traffic_data = []
        self.update_traffic_chart()

    # ---- HISTORY TAB ------------------------------------------------
    def build_history_tab(self):
        tab = self.notebook.tab("📋 History")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        self.history_box = CyberTextbox(tab, font=ctk.CTkFont(family="Consolas", size=11))
        self.history_box.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.update_history_display()

    # ---- ALERTS TAB -------------------------------------------------
    def build_alerts_tab(self):
        tab = self.notebook.tab("🔔 Alerts")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        self.alerts_box = CyberTextbox(tab, font=ctk.CTkFont(family="Consolas", size=11))
        self.alerts_box.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.alerts_box.insert("1.0", "🚨 Real-time Security Alerts\n\nMonitoring for threats...\n")

    # ---- ACTIVITY TAB -----------------------------------------------
    def build_activity_tab(self):
        tab = self.notebook.tab("⏱️ Activity")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        self.activity_box = CyberTextbox(tab, font=ctk.CTkFont(family="Consolas", size=11))
        self.activity_box.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

    # ---- SYSTEM TAB -------------------------------------------------
    def build_system_tab(self):
        tab = self.notebook.tab("💻 System")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        info_frame = CyberFrame(tab)
        info_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        sys_info = (f"\n  ⚡ SYSTEM INFORMATION\n  {'='*40}\n\n"
                    f"  OS:           {platform.system()} {platform.release()}\n"
                    f"  Machine:      {platform.machine()}\n"
                    f"  Processor:    {platform.processor()}\n"
                    f"  Python:       {platform.python_version()}\n"
                    f"  Architecture: {platform.architecture()[0]}\n"
                    f"  Hostname:     {platform.node()}\n\n"
                    f"  🔧 SCANNER STATUS\n  {'='*40}\n\n"
                    f"  Scanner: {'✅' if self.scanner_available else '❌'}\n"
                    f"  API:     {'✅' if self.api_available else '❌'}\n"
                    f"  Docker:  {'✅' if self.docker_available else '❌'}\n")
        ctk.CTkLabel(info_frame, text=sys_info, font=ctk.CTkFont(family="Consolas", size=11),
                     justify="left").pack(pady=20, padx=20)
        self.health_box = CyberTextbox(tab, font=ctk.CTkFont(family="Consolas", size=11))
        self.health_box.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.update_system_health()

    # ---- API STATS TAB ----------------------------------------------
    def build_api_tab(self):
        tab = self.notebook.tab("📊 API Stats")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        sf = CyberFrame(tab)
        sf.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        for i in range(3): sf.grid_columnconfigure(i, weight=1)
        self.api_total_label   = ctk.CTkLabel(sf, text="📊 Total: 0",   font=ctk.CTkFont(size=14, weight="bold"))
        self.api_success_label = ctk.CTkLabel(sf, text="✅ Success: 0", font=ctk.CTkFont(size=14), text_color=CYBER_SUCCESS)
        self.api_failed_label  = ctk.CTkLabel(sf, text="❌ Failed: 0",  font=ctk.CTkFont(size=14), text_color=CYBER_DANGER)
        self.api_avg_label     = ctk.CTkLabel(sf, text="⏱️ Avg: 0ms",  font=ctk.CTkFont(size=12), text_color=CYBER_INFO)
        self.api_total_label.grid(row=0, column=0, pady=10)
        self.api_success_label.grid(row=0, column=1, pady=10)
        self.api_failed_label.grid(row=0, column=2, pady=10)
        self.api_avg_label.grid(row=1, column=0, columnspan=3, pady=5)
        self.api_chart_box = CyberTextbox(tab, font=ctk.CTkFont(family="Consolas", size=11))
        self.api_chart_box.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.update_api_display()

    # ---- USER MANAGEMENT TAB ----------------------------------------
    def build_user_management_tab(self):
        tab = self.notebook.tab("👥 Users")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        uf = CyberFrame(tab)
        uf.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.user_list = ttk.Treeview(uf, columns=("Role",), show="tree headings", height=15)
        self.user_list.heading("#0", text="Username")
        self.user_list.heading("Role", text="Role")
        self.user_list.pack(fill="both", expand=True, padx=10, pady=10)
        self.refresh_user_list()
        af = ctk.CTkFrame(uf, fg_color="transparent")
        af.pack(pady=10)
        self.new_username = CyberEntry(af, placeholder_text="Username", width=180)
        self.new_username.pack(side="left", padx=5)
        self.new_password = CyberEntry(af, placeholder_text="Password", show="*", width=180)
        self.new_password.pack(side="left", padx=5)
        self.new_role = ttk.Combobox(af, values=["admin","user"], state="readonly", width=10)
        self.new_role.set("user")
        self.new_role.pack(side="left", padx=5)
        CyberButton(af, text="Add",    command=self.add_user).pack(side="left", padx=5)
        CyberButton(af, text="Delete", command=self.delete_user).pack(side="left", padx=5)

    def refresh_user_list(self):
        for item in self.user_list.get_children():
            self.user_list.delete(item)
        for u in self.users:
            self.user_list.insert("", "end", text=u["username"], values=(u["role"],))

    def add_user(self):
        uname = self.new_username.get()
        pwd   = self.new_password.get()
        role  = self.new_role.get()
        if uname and pwd:
            self.users.append({"username": uname, "password": pwd, "role": role})
            self.refresh_user_list()
            self.add_log("INFO", f"User {uname} added")
            self.add_notification("User Added", f"{uname} ({role})", "success")

    def delete_user(self):
        sel = self.user_list.selection()
        if sel:
            uname = self.user_list.item(sel[0], "text")
            self.users = [u for u in self.users if u["username"] != uname]
            self.refresh_user_list()
            self.add_log("INFO", f"User {uname} deleted")

    # ---- SUBSCRIPTION TAB -------------------------------------------
    def build_subscription_tab(self):
        tab = self.notebook.tab("💳 Subscription")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        info_frame = CyberFrame(tab)
        info_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        ctk.CTkLabel(info_frame, text="Current Plan",
                     font=ctk.CTkFont(size=14, weight="bold"), text_color=CYBER_CYAN).pack(pady=5)
        ctk.CTkLabel(info_frame, text=self.subscription['plan'],
                     font=ctk.CTkFont(size=20)).pack()
        ctk.CTkLabel(info_frame, text=f"Expires: {self.subscription['expires']}").pack()
        for feat in self.subscription['features']:
            ctk.CTkLabel(info_frame, text=f"✓ {feat}").pack()

        plans_frame = CyberFrame(tab)
        plans_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        ctk.CTkLabel(plans_frame, text="Upgrade Plans",
                     font=ctk.CTkFont(size=14, weight="bold"), text_color=CYBER_CYAN).pack(pady=5)
        for name, price, desc in [("Pro","$99/mo","Full features + AI"),
                                   ("Enterprise","$299/mo","Everything + API + Support")]:
            pc = ctk.CTkFrame(plans_frame, fg_color="transparent",
                              border_width=1, border_color=CYBER_CYAN)
            pc.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(pc, text=name,  font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=10)
            ctk.CTkLabel(pc, text=price).pack(side="left", padx=10)
            ctk.CTkLabel(pc, text=desc).pack(side="left", padx=10)
            CyberButton(pc, text="Select", width=80,
                        command=lambda n=name: self.upgrade_plan(n)).pack(side="right", padx=10)

    def upgrade_plan(self, plan):
        self.subscription["plan"] = plan
        self.subscription["expires"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        self.add_notification("Subscription", f"Upgraded to {plan}", "success")

    # ---- PLUGINS TAB ------------------------------------------------
    def build_plugins_tab(self):
        tab = self.notebook.tab("🔌 Plugins")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        pf = CyberFrame(tab)
        pf.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        for i, plugin in enumerate(self.plugins):
            row = ctk.CTkFrame(pf, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(row, text=plugin["name"],
                         font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=10)
            var = ctk.BooleanVar(value=plugin["enabled"])
            cb = ctk.CTkCheckBox(row, text="Enabled", variable=var,
                                 command=lambda idx=i, v=var: self.toggle_plugin(idx, v.get()))
            cb.pack(side="right", padx=10)
            if plugin["enabled"]: cb.select()
            else: cb.deselect()

    def toggle_plugin(self, idx, enabled):
        self.plugins[idx]["enabled"] = enabled
        self.add_log("INFO", f"Plugin {self.plugins[idx]['name']} "
                             f"{'enabled' if enabled else 'disabled'}")

    # ---- VM MANAGER TAB ---------------------------------------------
    def build_vm_manager_tab(self):
        tab = self.notebook.tab("🖥️ VMs")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        vmf = CyberFrame(tab)
        vmf.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.vm_tree = ttk.Treeview(vmf, columns=("Status","OS"), show="tree headings", height=15)
        self.vm_tree.heading("#0",     text="VM Name")
        self.vm_tree.heading("Status", text="Status")
        self.vm_tree.heading("OS",     text="OS")
        self.vm_tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.refresh_vm_list()
        bf = ctk.CTkFrame(vmf, fg_color="transparent")
        bf.pack(pady=10)
        CyberButton(bf, text="Start",  command=self.start_vm).pack(side="left", padx=5)
        CyberButton(bf, text="Stop",   command=self.stop_vm).pack(side="left", padx=5)
        CyberButton(bf, text="Add VM", command=self.add_vm).pack(side="left", padx=5)
        CyberButton(bf, text="Remove", command=self.remove_vm).pack(side="left", padx=5)

    def refresh_vm_list(self):
        for item in self.vm_tree.get_children():
            self.vm_tree.delete(item)
        for vm in self.vms:
            self.vm_tree.insert("", "end", text=vm["name"], values=(vm["status"], vm["os"]))

    def start_vm(self):
        sel = self.vm_tree.selection()
        if sel:
            name = self.vm_tree.item(sel[0], "text")
            for vm in self.vms:
                if vm["name"] == name: vm["status"] = "running"
            self.refresh_vm_list(); self.add_log("INFO", f"VM {name} started")

    def stop_vm(self):
        sel = self.vm_tree.selection()
        if sel:
            name = self.vm_tree.item(sel[0], "text")
            for vm in self.vms:
                if vm["name"] == name: vm["status"] = "stopped"
            self.refresh_vm_list(); self.add_log("INFO", f"VM {name} stopped")

    def add_vm(self):
        from tkinter.simpledialog import askstring
        name = askstring("Add VM", "Enter VM name:")
        if name:
            self.vms.append({"name": name, "status": "stopped", "os": "Unknown"})
            self.refresh_vm_list(); self.add_log("INFO", f"VM {name} added")

    def remove_vm(self):
        sel = self.vm_tree.selection()
        if sel:
            name = self.vm_tree.item(sel[0], "text")
            self.vms = [vm for vm in self.vms if vm["name"] != name]
            self.refresh_vm_list(); self.add_log("INFO", f"VM {name} removed")

    # ==================================================================
    # HELPER / UTILITY METHODS
    # ==================================================================

    def insert_cyber_header(self):
        header = (
            "\n╔══════════════════════════════════════════════════════════════╗\n"
            "║  ███╗   ██╗███████╗██╗   ██╗██████╗  ██████╗ ███╗   ██╗    ║\n"
            "║  ████╗  ██║██╔════╝██║   ██║██╔══██╗██╔═══██╗████╗  ██║    ║\n"
            "║  ██╔██╗ ██║█████╗  ██║   ██║██████╔╝██║   ██║██╔██╗ ██║    ║\n"
            "║  ██║╚██╗██║██╔══╝  ██║   ██║██╔══██╗██║   ██║██║╚██╗██║    ║\n"
            "║  ██║ ╚████║███████╗╚██████╔╝██║  ██║╚██████╔╝██║ ╚████║    ║\n"
            "║  ╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝   ║\n"
            "║              S E C U R I T Y   S C A N N E R               ║\n"
            "╠══════════════════════════════════════════════════════════════╣\n"
            "║  STATUS: READY  |  TARGET: NOT SPECIFIED  |  RISK: LOW     ║\n"
            "╚══════════════════════════════════════════════════════════════╝\n\n"
        )
        self.result_box.insert("1.0", header)

    def toggle_token_visibility(self):
        self.token_visible = not self.token_visible
        self.token_entry.configure(show="" if self.token_visible else "*")
        self.toggle_token_btn.configure(text="🔓" if self.token_visible else "👁️")

    def set_status(self, text, status_type="info"):
        colors = {"ready":CYBER_SUCCESS,"scanning":CYBER_WARNING,"error":CYBER_DANGER,
                  "success":CYBER_SUCCESS,"warning":CYBER_WARNING,"info":CYBER_INFO}
        icons  = {"ready":"✅","scanning":"⚡","error":"❌",
                  "success":"✅","warning":"⚠️","info":"ℹ️"}
        color = colors.get(status_type, CYBER_INFO)
        icon  = icons.get(status_type, "ℹ️")
        self.status_label.configure(text=f"{icon} STATUS: {text.upper()}", text_color=color)
        self.status_text.configure(text=f"SYSTEM {text.upper()}", text_color=color)
        indicator_color = CYBER_DANGER if status_type=="error" else \
                          CYBER_WARNING if status_type in ("warning","scanning") else CYBER_SUCCESS
        self.status_indicator.configure(fg_color=indicator_color)
        self.add_log("INFO", f"Status: {text.upper()}")

    def set_progress(self, value):
        self.progress.set(value)

    def set_results(self, lines, findings_count=0):
        self.result_lines = lines[:]
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.insert_cyber_header()
        for line in lines:
            self.insert_colored_line(line)
        self.result_box.configure(state="disabled")
        self.summary_label.configure(text=f"🔍 Vulnerabilities: {findings_count}")
        if hasattr(self, 'stats_labels') and len(self.stats_labels) > 1:
            self.stats_labels[1].configure(text=str(findings_count))
        self.update_threat_level(findings_count)
        self.update_dashboard_stats()

    def update_threat_level(self, n):
        if   n > 20: level,color,val = "CRITICAL",CYBER_DANGER,0.95
        elif n > 10: level,color,val = "HIGH",    CYBER_WARNING,0.75
        elif n > 5:  level,color,val = "MEDIUM",  CYBER_WARNING,0.5
        elif n > 0:  level,color,val = "LOW",     CYBER_INFO,   0.25
        else:        level,color,val = "NONE",    CYBER_SUCCESS,0.05
        if hasattr(self, 'threat_meter'):
            self.threat_meter.set(val)
            self.threat_meter.configure(progress_color=color)
            icon = "🟢" if val <= 0.25 else "🟡" if val <= 0.5 else "🔴"
            self.threat_label.configure(text=f"{icon} {level} RISK", text_color=color)

    def update_dashboard_stats(self):
        if not hasattr(self, 'stats_labels'): return
        if len(self.stats_labels) > 0:
            self.stats_labels[0].configure(text=str(len(self.scan_history)))
        if len(self.stats_labels) > 2:
            rate = (self.api_stats["success"]/max(1,self.api_stats["total"]))*100
            self.stats_labels[2].configure(text=f"{rate:.0f}%")
        if len(self.stats_labels) > 3:
            self.stats_labels[3].configure(text=str(self.api_stats["total"]))

    def insert_colored_line(self, line):
        start = self.result_box.index("end-1c")
        self.result_box.insert("end", line + "\n")
        end = self.result_box.index("end-1c")
        lu = line.upper()
        if   "[CRITICAL]" in lu: tag,fg = "critical",CYBER_DANGER
        elif "[HIGH]"     in lu: tag,fg = "high",    "#ff6b6b"
        elif "[MEDIUM]"   in lu: tag,fg = "medium",  "#ffd166"
        elif "[LOW]"      in lu: tag,fg = "low",     "#66b3ff"
        elif "[INFO]"     in lu: tag,fg = "info",    "#b0b7c3"
        else:                    return
        self.result_box.tag_add(tag, start, end)
        self.result_box.tag_config(tag, foreground=fg)

    def clear_results(self):
        self.last_result = None
        self.result_lines = []
        self.set_results(["No scan results yet. Enter a target URL and click START LOCAL SCAN."], 0)
        self.set_status("READY"); self.set_progress(0)
        self.add_log("INFO", "Results cleared")

    def validate_target(self):
        target = self.url_entry.get().strip()
        if not target:
            messagebox.showerror("Error", "Target URL is required!")
            return None
        if not target.startswith(('http://','https://')):
            target = 'http://' + target
        return target

    def copy_results(self):
        if not self.result_lines:
            messagebox.showwarning("Warning", "No results to copy."); return
        self.clipboard_clear()
        self.clipboard_append("\n".join(self.result_lines))
        messagebox.showinfo("Success", "Results copied to clipboard!")
        self.add_log("SUCCESS", "Results copied to clipboard")

    def export_pdf(self):
        if not self.result_lines:
            messagebox.showwarning("Warning", "No results to export."); return
        fp = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF files","*.pdf")],
            initialfile=f"cyber_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        if not fp: return
        try:
            c = canvas.Canvas(fp, pagesize=A4)
            w, h = A4
            c.setFont("Helvetica-Bold", 20); c.setFillColorRGB(0,1,1)
            c.drawString(40, h-50, "NEURON SECURITY LAB - CYBER SCAN REPORT")
            c.setFont("Helvetica", 10); c.setFillColorRGB(.5,.5,.5)
            c.drawString(40, h-75, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            c.drawString(40, h-90, f"Target: {self.url_entry.get().strip() or '-'}")
            y = h-120; c.setFont("Helvetica", 9); c.setFillColorRGB(1,1,1)
            for line in self.result_lines:
                if y < 50: c.showPage(); y = h-50; c.setFont("Helvetica",9)
                c.drawString(40, y, line[:110]); y -= 14
            c.save()
            messagebox.showinfo("Success", f"PDF saved:\n{fp}")
            self.add_log("SUCCESS", f"PDF exported: {fp}")
        except Exception as e:
            messagebox.showerror("Error", f"PDF export failed:\n{e}")
            self.add_log("ERROR", f"PDF export failed: {e}")

    def export_csv(self):
        if not self.result_lines:
            messagebox.showwarning("Warning", "No results to export."); return
        fp = filedialog.asksaveasfilename(defaultextension=".csv",
                                          filetypes=[("CSV files","*.csv")])
        if not fp: return
        try:
            with open(fp, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Severity","Type","Detail","Recommendation"])
                for line in self.result_lines:
                    if "[" in line and "]" in line and "-" in line:
                        parts = line.split(" - ", 1)
                        if len(parts) == 2:
                            writer.writerow([parts[0].strip("[] "), "", parts[1], ""])
            messagebox.showinfo("Success", f"CSV saved:\n{fp}")
            self.add_log("SUCCESS", "CSV exported")
        except Exception as e:
            messagebox.showerror("Error", f"CSV export failed: {e}")

    def cancel_scan(self):
        self.is_scanning = False
        self.set_status("CANCELLED", "warning")
        self.add_log("WARNING", "Scan cancelled by user")

    def toggle_theme(self):
        ctk.set_appearance_mode(self.theme_var.get())
        self.add_log("INFO", f"Theme changed to {self.theme_var.get()}")

    def disable_buttons(self):
        for btn in (self.scan_button, self.cloud_button, self.remote_scan_btn,
                    self.copy_btn, self.pdf_btn, self.csv_btn):
            btn.configure(state="disabled")

    def enable_buttons(self):
        for btn in (self.scan_button, self.cloud_button, self.remote_scan_btn,
                    self.copy_btn, self.pdf_btn, self.csv_btn):
            btn.configure(state="normal")

    def show_help(self):
        messagebox.showinfo("Help Guide",
            "NEURON SECURITY LAB - Help\n\n"
            "🎯 Scanner Tab:\n"
            "  - Enter target URL\n"
            "  - Click START LOCAL SCAN / SCAN + CLOUD SYNC\n"
            "  - REMOTE SCAN uses active SSH connection\n\n"
            "⌨️ Shortcuts:\n"
            "  Ctrl+S  Start Scan\n"
            "  Ctrl+E  Export PDF\n"
            "  Ctrl+C  Copy Results\n"
            "  Ctrl+L  Clear Results\n"
            "  F1      Help\n"
            "  F5      Refresh\n"
            "  Esc     Cancel Scan")

    def refresh_all(self):
        self.load_scan_history(); self.update_history_display()
        self.update_dashboard_stats(); self.update_system_health()
        self.add_log("INFO", "UI refreshed")

    # ==================================================================
    # SCAN METHODS
    # ==================================================================

    def run_scan(self):
        target = self.validate_target()
        if not target:
            self.after(0, lambda: self.set_status("READY")); return
        self.after(0, self.disable_buttons)
        self.after(0, lambda: self.set_progress(0.1))
        self.after(0, lambda: self.set_status("SCANNING", "scanning"))
        self.after(0, lambda: self.set_results(["🔍 Initializing cyber scan...\n"], 0))
        self.add_log("INFO", f"Starting scan on {target}")

        if not self.scanner_available:
            self.after(0, lambda: self.set_results(
                ["[ERROR] Scanner engine not available!",
                 "[INFO] Ensure scanner_engine.py is present."], 1))
            self.after(0, lambda: self.set_progress(1))
            self.after(0, lambda: self.set_status("ERROR", "error"))
            self.after(0, self.enable_buttons); return

        try:
            for i in range(1, 11):
                if not self.is_scanning: break
                self.after(0, lambda v=i/10: self.set_progress(v))
                time.sleep(0.3)

            result = scan_target(target, timeout=int(self.timeout_var.get()))
            self.last_result = result
            self.after(0, lambda: self.set_progress(0.95))
            findings = result.get("findings", [])
            lines = []

            if result.get("status") == "error":
                for item in findings:
                    lines.append(f"[{item.get('severity','unknown').upper()}] {item.get('detail','')}")
                self.after(0, lambda: self.set_results(lines, len(findings)))
                self.after(0, lambda: self.set_progress(1))
                self.after(0, lambda: self.set_status("SCAN FAILED", "error"))
                return

            for i, item in enumerate(findings, 1):
                sev   = item.get("severity","info").upper()
                ftype = item.get("type","issue")
                detail= item.get("detail","No detail")
                rec   = item.get("recommendation","No recommendation")
                lines += [f"{i}. [{sev}] {ftype} - {detail}",
                          f"    🔧 Remediation: {rec}", ""]

            self.after(0, lambda: self.set_results(lines, len(findings)))
            self.after(0, lambda: self.set_progress(1))
            self.after(0, lambda: self.set_status("SCAN COMPLETED", "success"))
            self.add_log("SUCCESS", f"Scan completed: {len(findings)} findings")
            self.scan_history.append({"id": len(self.scan_history)+1, "target": target,
                                      "time": datetime.now().isoformat(), "findings": len(findings),
                                      "status": "completed", "scan_type": "local"})
            self.save_scan_history(); self.update_history_display()
            self.add_activity("Scan Completed", f"Target: {target}, Findings: {len(findings)}")
            self.add_notification("Scan Complete", f"Found {len(findings)} vulns on {target}", "info")
            self.update_dashboard_stats()
        except Exception as e:
            self.after(0, lambda: self.set_results([f"[ERROR] {e}"], 1))
            self.after(0, lambda: self.set_progress(1))
            self.after(0, lambda: self.set_status("ERROR", "error"))
            self.add_log("ERROR", f"Scan error: {e}")
        finally:
            self.after(0, self.enable_buttons)

    def start_scan_thread(self):
        self.is_scanning = True
        threading.Thread(target=self.run_scan, daemon=True).start()

    def run_send(self):
        target = self.validate_target()
        if not target:
            self.after(0, lambda: self.set_status("READY")); return
        api_token = self.token_entry.get().strip()
        if not api_token:
            messagebox.showerror("Error", "API token is required!")
            self.after(0, lambda: self.set_status("READY")); return
        self.after(0, self.disable_buttons)
        self.after(0, lambda: self.set_status("SCANNING + CLOUD", "scanning"))
        self.after(0, lambda: self.set_progress(0.1))
        self.add_log("INFO", f"Cloud scan: {target}")

        if not self.scanner_available or not self.api_available:
            self.after(0, lambda: self.set_results(
                ["[ERROR] Scanner or API client not available!"], 1))
            self.after(0, lambda: self.set_progress(1))
            self.after(0, lambda: self.set_status("ERROR", "error"))
            self.after(0, self.enable_buttons); return

        start_time = time.time()
        try:
            result = scan_target(target, timeout=int(self.timeout_var.get()))
            self.last_result = result
            self.after(0, lambda: self.set_progress(0.6))
            response = submit_scan_results(SERVER_URL, api_token,
                                           result["target_url"], result["findings"])
            response_time = (time.time()-start_time)*1000
            self.after(0, lambda: self.set_progress(0.9))
            findings = result.get("findings", [])
            lines = []
            for i, item in enumerate(findings, 1):
                sev   = item.get("severity","info").upper()
                ftype = item.get("type","issue")
                detail= item.get("detail","No detail")
                rec   = item.get("recommendation","No recommendation")
                lines += [f"{i}. [{sev}] {ftype} - {detail}",
                          f"    🔧 Remediation: {rec}", ""]
            lines += ["", "[INFO] ☁️ CLOUD SYNC STATUS:",
                      f"[INFO] Status: {response.status_code}",
                      f"[INFO] Response: {response.text[:200]}"]
            self.after(0, lambda: self.set_results(lines, len(findings)))
            self.after(0, lambda: self.set_progress(1))
            if response.status_code == 200:
                self.after(0, lambda: self.set_status("CLOUD SYNC SUCCESS","success"))
                self.add_log("SUCCESS", "Results sent to cloud")
                self.add_notification("Cloud Sync", "Sent successfully", "success")
                self.update_api_stats(True, response_time)
                self.scan_history.append({"id": len(self.scan_history)+1, "target": target,
                                          "time": datetime.now().isoformat(), "findings": len(findings),
                                          "status": "synced", "scan_type": "cloud"})
            else:
                self.after(0, lambda: self.set_status("CLOUD ERROR","error"))
                self.add_log("ERROR", f"Cloud sync failed: {response.status_code}")
                self.update_api_stats(False, response_time)
        except Exception as e:
            self.after(0, lambda: self.set_results([f"[ERROR] {e}"], 1))
            self.after(0, lambda: self.set_progress(1))
            self.after(0, lambda: self.set_status("ERROR","error"))
            self.add_log("ERROR", f"Send error: {e}")
            self.update_api_stats(False)
        finally:
            self.after(0, self.enable_buttons)
            self.save_scan_history(); self.update_history_display()
            self.update_dashboard_stats()

    def send_scan_thread(self):
        self.is_scanning = True
        threading.Thread(target=self.run_send, daemon=True).start()

    def start_remote_scan(self):
        target = self.validate_target()
        if not target: return
        if not self.ssh_client:
            messagebox.showerror("Error", "SSH not connected. Connect first in Network tab.")
            return
        self.add_log("INFO", f"Remote scan: {target}")
        threading.Thread(target=self.run_remote_scan, args=(target,), daemon=True).start()

    def run_remote_scan(self, target):
        cmd = (f"python -c \"from scanner_engine import scan_target; import json; "
               f"print(json.dumps(scan_target('{target}')))\"")
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(cmd, timeout=60)
            output = stdout.read().decode(); error = stderr.read().decode()
            if error: self.add_log("ERROR", f"Remote scan error: {error}"); return
            result = json.loads(output)
            findings = result.get("findings", [])
            lines = []
            for i, item in enumerate(findings, 1):
                sev   = item.get("severity","info").upper()
                ftype = item.get("type","issue")
                detail= item.get("detail","No detail")
                rec   = item.get("recommendation","No recommendation")
                lines += [f"{i}. [{sev}] {ftype} - {detail}",
                          f"    🔧 Remediation: {rec}", ""]
            self.after(0, lambda: self.set_results(lines, len(findings)))
            self.add_log("SUCCESS", f"Remote scan done: {len(findings)} findings")
        except Exception as e:
            self.add_log("ERROR", f"Remote scan failed: {e}")

    # ==================================================================
    # SSH METHODS
    # ==================================================================

    def connect_ssh(self):
        host = self.ssh_host.get(); port = int(self.ssh_port.get() or 22)
        user = self.ssh_user.get(); password = self.ssh_pass.get()
        if not all([host, user, password]):
            self.terminal_box.insert("end", "\n❌ Please fill in host, user, and password\n"); return
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(host, port, user, password, timeout=10)
            self.ssh_connected = True
            self.terminal_box.insert("end", f"\n✅ Connected to {host}:{port} as {user}\n")
            self.terminal_box.see("end")
            self.add_log("SUCCESS", f"SSH connected to {host}")
            self.ssh_connect_btn.configure(text="CONNECTED ✅", fg_color=CYBER_SUCCESS)
        except Exception as e:
            self.terminal_box.insert("end", f"\n❌ Connection failed: {e}\n")
            self.terminal_box.see("end")
            self.add_log("ERROR", f"SSH connection failed: {e}")

    def execute_ssh_command(self):
        if not self.ssh_client:
            self.terminal_box.insert("end", "\n⚠️ Not connected.\n"); return
        cmd = self.cmd_entry.get()
        if not cmd: return
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(cmd, timeout=30)
            out = stdout.read().decode(); err = stderr.read().decode()
            self.terminal_box.insert("end", f"\n$ {cmd}\n")
            if out: self.terminal_box.insert("end", out)
            if err: self.terminal_box.insert("end", f"Error: {err}\n")
            self.terminal_box.see("end"); self.cmd_entry.delete(0, "end")
            self.add_log("INFO", f"SSH cmd: {cmd}")
        except Exception as e:
            self.terminal_box.insert("end", f"\n❌ Command failed: {e}\n")
            self.terminal_box.see("end")
            self.add_log("ERROR", f"SSH command failed: {e}")

    # ==================================================================
    # DATABASE METHODS
    # ==================================================================

    def connect_database(self):
        db_path = self.db_path_entry.get() or "siteguard.db"
        if not os.path.exists(db_path):
            self.tables_list.delete("1.0","end")
            self.tables_list.insert("1.0", f"Not found:\n{db_path}"); return
        try:
            self.db_conn   = sqlite3.connect(db_path)
            self.db_cursor = self.db_conn.cursor()
            self.db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = self.db_cursor.fetchall()
            self.tables_list.delete("1.0","end")
            for t in tables: self.tables_list.insert("end", f"📋 {t[0]}\n")
            self.data_box.delete("1.0","end")
            self.data_box.insert("1.0", f"✅ Connected: {db_path}\n{len(tables)} tables found.\n")
            self.add_log("SUCCESS", f"DB connected: {db_path}")
            self.tables_list.bind("<Button-1>", self.on_table_select)
        except Exception as e:
            self.tables_list.delete("1.0","end")
            self.tables_list.insert("1.0", f"Error: {e}")
            self.add_log("ERROR", f"DB connect failed: {e}")

    def on_table_select(self, event):
        try:
            idx  = self.tables_list.index("@%d,%d" % (event.x, event.y))
            line = self.tables_list.get(f"{idx} linestart", f"{idx} lineend")
            name = line.replace("📋 ","").strip()
            if name and hasattr(self,'db_cursor'):
                self.db_cursor.execute(f"SELECT * FROM {name} LIMIT 50")
                rows = self.db_cursor.fetchall()
                self.db_cursor.execute(f"PRAGMA table_info({name})")
                cols = [c[1] for c in self.db_cursor.fetchall()]
                self.data_box.delete("1.0","end")
                self.data_box.insert("1.0", f"Table: {name}\nColumns: {', '.join(cols)}\n{'='*50}\n\n")
                for row in rows: self.data_box.insert("end", f"{row}\n")
                self.data_box.insert("end", f"\n{len(rows)} rows shown.")
                self.add_log("INFO", f"Viewed table: {name}")
        except Exception: pass

    # ==================================================================
    # FILE EXPLORER  (LAZY LOAD — no recursion crash)
    # ==================================================================

    def get_drives(self):
        if platform.system() == "Windows":
            import string
            from ctypes import windll
            drives, mask = [], windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if mask & 1: drives.append(f"{letter}:\\")
                mask >>= 1
            return drives
        return ["/"]

    def on_drive_select(self, event):
        drive = self.drive_combo.get()
        if drive: self.load_file_system(drive)

    def load_file_system(self, path):
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        try:
            root_id = self.file_tree.insert("", "end",
                                            text=os.path.basename(path) or path,
                                            values=(path,), open=True)
            self._lazy_populate(root_id, path)
            self.file_status.configure(text=f"Loaded: {path}")
        except Exception as e:
            self.file_status.configure(text=f"Error: {str(e)[:60]}")
            self.add_log("ERROR", f"File system error: {e}")

    def _lazy_populate(self, parent_id, path):
        """Insert one level of directory entries; add placeholder for sub-dirs."""
        try:
            entries = sorted(os.scandir(path),
                             key=lambda e: (not e.is_dir(), e.name.lower()))
        except (PermissionError, OSError):
            return
        for entry in list(entries)[:300]:
            if entry.name.startswith('.'): continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    node = self.file_tree.insert(parent_id, "end", text=entry.name,
                                                 values=(entry.path,), open=False)
                    # placeholder so expand arrow appears
                    try:
                        if any(True for _ in os.scandir(entry.path)):
                            self.file_tree.insert(node, "end",
                                                  text="__loading__", values=("",))
                    except (PermissionError, OSError):
                        pass
                else:
                    try:   size_str = self.format_size(entry.stat().st_size)
                    except OSError: size_str = "?"
                    self.file_tree.insert(parent_id, "end", text=entry.name,
                                          values=(entry.path, size_str))
            except (PermissionError, OSError):
                continue

    def _on_tree_expand(self, event):
        """Load children lazily when the user expands a folder."""
        node = self.file_tree.focus()
        children = self.file_tree.get_children(node)
        if len(children) == 1 and self.file_tree.item(children[0], "text") == "__loading__":
            self.file_tree.delete(children[0])
            path = self.file_tree.item(node, "values")[0]
            if path and os.path.isdir(path):
                self._lazy_populate(node, path)

    def format_size(self, size):
        for unit in ['B','KB','MB','GB']:
            if size < 1024.0: return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def on_file_select(self, event):
        sel = self.file_tree.selection()
        if not sel: return
        item = self.file_tree.item(sel[0])
        path = item['values'][0] if item['values'] else None
        if not path or os.path.isdir(path): return
        try:
            ext = os.path.splitext(path)[1].lower()
            text_ext = {'.txt','.py','.js','.html','.css','.json','.xml','.md',
                        '.ini','.cfg','.conf','.log','.csv','.sh','.bat','.yaml','.yml'}
            if ext in text_ext and os.path.getsize(path) < 1024*1024:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(50000)
                self.file_content.delete("1.0","end")
                self.file_content.insert("1.0", content)
                if len(content) >= 50000:
                    self.file_content.insert("end", "\n\n... (truncated)")
                self.file_status.configure(text=f"Loaded: {os.path.basename(path)}")
            else:
                self.file_content.delete("1.0","end")
                self.file_content.insert("1.0", "Preview not available for this file type or size.")
                self.file_status.configure(text="Preview not available")
        except Exception as e:
            self.file_content.delete("1.0","end")
            self.file_content.insert("1.0", f"Error reading file:\n{e}")
            self.file_status.configure(text="Error")

    def on_file_drop(self, event):
        try:
            files = self.tk.splitlist(event.data)
            if files:
                path = files[0].strip('{}')
                self.drop_area.delete("1.0","end")
                self.drop_area.insert("1.0", path)
                self.scan_file(path)
        except Exception: pass

    def scan_file(self, file_path):
        self.add_log("INFO", f"File drop: {file_path}")
        self.set_results([f"[INFO] File dropped: {file_path}",
                          "[INFO] Use URL field for a full network scan."], 0)

    # ==================================================================
    # DOCKER METHODS
    # ==================================================================

    def load_docker_containers(self):
        if not self.docker_available or not self.docker_client: return
        try:
            containers = self.docker_client.containers.list(all=True)
            self.docker_box.delete("1.0","end")
            self.docker_box.insert("1.0","🐳 DOCKER CONTAINERS\n\n")
            for c in containers:
                status = "🟢 Running" if c.status=="running" else "🔴 Stopped"
                self.docker_box.insert("end",
                    f"📦 {c.name}\n"
                    f"   ID:      {c.id[:12]}\n"
                    f"   Status:  {status}\n"
                    f"   Image:   {c.image.tags[0] if c.image.tags else 'none'}\n"
                    f"   Created: {c.attrs['Created'][:19]}\n\n")
        except Exception as e:
            self.docker_box.insert("end", f"Error: {e}")

    # ==================================================================
    # AI ASSISTANT
    # ==================================================================

    def process_ai_query(self):
        query = self.ai_input.get().strip()
        if not query: return
        self.ai_box.insert("end", f"\n🤔 You: {query}\n🤖 AI: ")
        self.ai_box.update()
        for ch in self.generate_ai_response(query.lower()):
            self.ai_box.insert("end", ch); self.ai_box.update(); time.sleep(0.01)
        self.ai_box.insert("end", "\n\n"); self.ai_box.see("end")
        self.ai_input.delete(0,"end")
        self.add_log("INFO", f"AI query: {query[:50]}")

    def generate_ai_response(self, q):
        if "sql" in q:
            return ("SQL Injection Prevention:\n"
                    "1. Use parameterized queries / prepared statements\n"
                    "2. Validate and whitelist input\n"
                    "3. Apply least-privilege DB accounts\n"
                    "4. Use an ORM framework\n"
                    "5. Deploy a Web Application Firewall")
        if "xss" in q or "cross-site" in q:
            return ("XSS Prevention:\n"
                    "1. Encode output by context (HTML, JS, URL)\n"
                    "2. Implement strict Content-Security-Policy\n"
                    "3. Sanitize input with DOMPurify\n"
                    "4. Set HttpOnly & Secure flags on cookies\n"
                    "5. Add X-XSS-Protection header")
        if "port" in q:
            return ("Common Ports:\n"
                    "80 HTTP  |  443 HTTPS  |  22 SSH\n"
                    "21 FTP   |  3306 MySQL |  5432 PostgreSQL\n"
                    "27017 MongoDB  |  6379 Redis  |  8080 Alt-HTTP")
        if "scan" in q:
            return ("How to scan:\n"
                    "1. Enter target URL in the Scanner tab\n"
                    "2. Choose Deep Scan / Port Scanning\n"
                    "3. Click START LOCAL SCAN\n"
                    "4. Review colour-coded results\n"
                    "5. Export as PDF or CSV")
        if "api" in q and "token" in q:
            return "API Token: Find it in your dashboard under 'Desktop Agent Settings'. Treat it like a password."
        return (f"I specialise in cybersecurity topics.\n"
                f"Try asking about: SQL injection, XSS, port scanning, scan setup, or API tokens.")

    # ==================================================================
    # TRAFFIC CHART
    # ==================================================================

    def update_traffic_chart(self):
        val = random.randint(50, 500)
        self.traffic_data.append(val)
        if len(self.traffic_data) > 60: self.traffic_data.pop(0)
        self.traffic_line.set_data(range(len(self.traffic_data)), self.traffic_data)
        ax = self.traffic_canvas.figure.gca()
        ax.relim(); ax.autoscale_view()
        ax.set_title(f"Real-time Network Traffic — {val} pkt/s", color=CYBER_CYAN)
        self.traffic_canvas.draw()
        self.after(1000, self.update_traffic_chart)

    # ==================================================================
    # HISTORY / SYSTEM / API DISPLAY
    # ==================================================================

    def update_history_display(self):
        if not hasattr(self,'history_box'): return
        self.history_box.configure(state="normal")
        self.history_box.delete("1.0","end")
        if not self.scan_history:
            self.history_box.insert("1.0","No scan history yet.")
        else:
            for scan in self.scan_history[-30:]:
                icon = "✅" if scan['status']=="completed" else "☁️" if scan['status']=="synced" else "⚠️"
                self.history_box.insert("end",
                    f"{icon} Scan #{scan['id']}\n"
                    f"   🎯 {scan['target']}\n"
                    f"   🕒 {scan['time'][:19]}\n"
                    f"   🔍 {scan['findings']} findings\n"
                    f"   📡 {scan.get('scan_type','local')}\n\n")
        self.history_box.configure(state="disabled")

    def update_system_health(self):
        if not hasattr(self,'health_box'): return
        cpu  = psutil.cpu_percent()
        ram  = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        boot = datetime.fromtimestamp(psutil.boot_time())
        up   = str(datetime.now()-boot).split('.')[0]
        net  = psutil.net_io_counters()
        if hasattr(self,'cpu_bar'):
            self.cpu_bar.set(cpu/100); self.ram_bar.set(ram/100); self.disk_bar.set(disk/100)
            self.cpu_label_dash.configure(text=f"CPU: {cpu}%")
            self.ram_label_dash.configure(text=f"RAM: {ram}%")
            self.disk_label.configure(text=f"DISK: {disk}%")
        ci = '🟢' if cpu<50 else '🟡' if cpu<80 else '🔴'
        ri = '🟢' if ram<70 else '🟡' if ram<90 else '🔴'
        di = '🟢' if disk<70 else '🟡' if disk<90 else '🔴'
        text = (f"\n╔{'═'*60}╗\n"
                f"║{'  SYSTEM HEALTH MONITOR':^60}║\n"
                f"╠{'═'*60}╣\n"
                f"║  💻 CPU:    {cpu:>5}%  {ci:<52}║\n"
                f"║  🧠 RAM:    {ram:>5}%  {ri:<52}║\n"
                f"║  💾 Disk:   {disk:>5}%  {di:<52}║\n"
                f"║  ⏰ Uptime: {up:<52}║\n"
                f"║  🔄 PIDs:   {len(psutil.pids()):<52}║\n"
                f"║  📡 Sent:   {net.bytes_sent/1024/1024:.1f} MB{'':<47}║\n"
                f"║  📡 Recv:   {net.bytes_recv/1024/1024:.1f} MB{'':<47}║\n"
                f"╚{'═'*60}╝\n")
        self.health_box.delete("1.0","end")
        self.health_box.insert("1.0", text)

    def update_api_display(self):
        if not hasattr(self,'api_chart_box'): return
        rt   = self.api_stats['response_time']
        avg  = sum(rt)/max(1,len(rt))
        text = (f"\n╔{'═'*60}╗\n"
                f"║{'  API USAGE STATISTICS':^60}║\n"
                f"╠{'═'*60}╣\n"
                f"║  Total:    {self.api_stats['total']:<50}║\n"
                f"║  Success:  {self.api_stats['success']:<50}║\n"
                f"║  Failed:   {self.api_stats['failed']:<50}║\n"
                f"║  Avg RT:   {avg:.0f} ms{'':<47}║\n"
                f"╠{'═'*60}╣\n"
                f"║  Recent response times:{'':37}║\n")
        for i, r in enumerate(rt[-15:], 1):
            bar = '█' * int(r/max(rt[-15:] or [1])*30)
            text += f"║  {i:2d}. {r:4.0f}ms  {bar:<40}║\n"
        text += f"╚{'═'*60}╝\n"
        self.api_chart_box.delete("1.0","end")
        self.api_chart_box.insert("1.0", text)

    # ==================================================================
    # SEARCH / LOCAL TERMINAL
    # ==================================================================

    def search_logs(self):
        q = self.search_entry.get().lower()
        if not q: return
        self.log_box.configure(state="normal")
        self.log_box.tag_remove("highlight","1.0","end")
        start, count = "1.0", 0
        while True:
            pos = self.log_box.search(q, start, stopindex="end", nocase=True)
            if not pos: break
            end = f"{pos}+{len(q)}c"
            self.log_box.tag_add("highlight", pos, end)
            start = end; count += 1
        self.log_box.tag_config("highlight", background=CYBER_WARNING, foreground="black")
        self.log_box.configure(state="disabled")
        self.add_log("INFO", f"Found {count} matches for '{q}'")

    def execute_local_command(self):
        cmd = self.term_input.get()
        if not cmd: return
        self.local_terminal.insert("end", f"\n$ {cmd}\n")
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            if res.stdout: self.local_terminal.insert("end", res.stdout)
            if res.stderr: self.local_terminal.insert("end", f"⚠️ {res.stderr}\n")
            self.local_terminal.insert("end", f"[exit {res.returncode}]\n")
        except subprocess.TimeoutExpired:
            self.local_terminal.insert("end", "⚠️ Command timed out (30s)\n")
        except Exception as e:
            self.local_terminal.insert("end", f"❌ Error: {e}\n")
        self.local_terminal.see("end"); self.term_input.delete(0,"end")
        self.add_log("INFO", f"Local cmd: {cmd}")

    # ==================================================================
    # NEW WINDOW
    # ==================================================================

    def open_new_window(self):
        win = ctk.CTkToplevel(self)
        win.title("Neuron Security — New Window")
        win.geometry("800x600")
        win.configure(fg_color=CYBER_DARKER)
        ctk.CTkLabel(win, text="Additional Window",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=CYBER_CYAN).pack(expand=True)


# ==============================================================
# ENTRY POINT
# ==============================================================
if __name__ == "__main__":
    app = DesktopScannerApp()
    app.update_idletasks()
    w = app.winfo_width(); h = app.winfo_height()
    x = (app.winfo_screenwidth()  // 2) - (w // 2)
    y = (app.winfo_screenheight() // 2) - (h // 2)
    app.geometry(f"{w}x{h}+{x}+{y}")
    app.mainloop()