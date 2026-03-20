import os
import threading
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox, filedialog

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from scanner_engine import scan_target
from api_client import submit_scan_results
from config import SERVER_URL, DEFAULT_TIMEOUT


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DesktopScannerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Security Lab - Desktop Local Scanner")
        self.geometry("1100x760")
        self.minsize(980, 680)

        self.last_result = None
        self.result_lines = []

        self.set_window_icon()
        self.build_ui()

    def set_window_icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(self, corner_radius=18)
        header_frame.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        header_frame.grid_columnconfigure(1, weight=1)

        logo_label = ctk.CTkLabel(
            header_frame,
            text="🛡️ AI Security Lab",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        logo_label.grid(row=0, column=0, padx=18, pady=(16, 4), sticky="w")

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Localhost va local IP saytlar uchun xavfsizlik tekshiruvi",
            font=ctk.CTkFont(size=13)
        )
        subtitle_label.grid(row=1, column=0, padx=18, pady=(0, 16), sticky="w")

        self.progress = ctk.CTkProgressBar(header_frame, height=10)
        self.progress.grid(row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 16))
        self.progress.set(0)

        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        content_frame.grid_columnconfigure(0, weight=0)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        left_panel = ctk.CTkFrame(content_frame, corner_radius=18, width=340)
        left_panel.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        left_panel.grid_propagate(False)

        form_title = ctk.CTkLabel(
            left_panel,
            text="Scan sozlamalari",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        form_title.pack(anchor="w", padx=18, pady=(18, 10))

        url_label = ctk.CTkLabel(left_panel, text="Target URL")
        url_label.pack(anchor="w", padx=18, pady=(8, 4))

        self.url_entry = ctk.CTkEntry(
            left_panel,
            width=300,
            height=42,
            placeholder_text="http://localhost:5000"
        )
        self.url_entry.pack(padx=18, pady=(0, 10))

        token_label = ctk.CTkLabel(left_panel, text="API Token")
        token_label.pack(anchor="w", padx=18, pady=(8, 4))

        token_row = ctk.CTkFrame(left_panel, fg_color="transparent")
        token_row.pack(fill="x", padx=18, pady=(0, 10))

        self.token_entry = ctk.CTkEntry(
            token_row,
            width=220,
            height=42,
            placeholder_text="Dashboard tokeni",
            show="*"
        )
        self.token_entry.pack(side="left", padx=(0, 8))

        self.show_token = False
        self.toggle_token_btn = ctk.CTkButton(
            token_row,
            text="Show",
            width=70,
            height=42,
            command=self.toggle_token_visibility
        )
        self.toggle_token_btn.pack(side="left")

        server_label = ctk.CTkLabel(left_panel, text="Cloud Server")
        server_label.pack(anchor="w", padx=18, pady=(8, 4))

        self.server_entry = ctk.CTkEntry(
            left_panel,
            width=300,
            height=42
        )
        self.server_entry.insert(0, SERVER_URL)
        self.server_entry.pack(padx=18, pady=(0, 14))

        self.scan_button = ctk.CTkButton(
            left_panel,
            text="Start Local Scan",
            height=42,
            corner_radius=12,
            command=self.start_scan_thread
        )
        self.scan_button.pack(fill="x", padx=18, pady=(6, 8))

        self.send_button = ctk.CTkButton(
            left_panel,
            text="Scan + Send to Cloud",
            height=42,
            corner_radius=12,
            command=self.send_scan_thread
        )
        self.send_button.pack(fill="x", padx=18, pady=(0, 8))

        self.copy_button = ctk.CTkButton(
            left_panel,
            text="Copy Result",
            height=40,
            corner_radius=12,
            command=self.copy_results
        )
        self.copy_button.pack(fill="x", padx=18, pady=(0, 8))

        self.pdf_button = ctk.CTkButton(
            left_panel,
            text="Export PDF",
            height=40,
            corner_radius=12,
            command=self.export_pdf
        )
        self.pdf_button.pack(fill="x", padx=18, pady=(0, 8))

        self.clear_button = ctk.CTkButton(
            left_panel,
            text="Clear Results",
            height=40,
            corner_radius=12,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.clear_results
        )
        self.clear_button.pack(fill="x", padx=18, pady=(0, 8))

        self.status_label = ctk.CTkLabel(
            left_panel,
            text="Status: Ready",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.status_label.pack(anchor="w", padx=18, pady=(14, 6))

        hint_box = ctk.CTkTextbox(left_panel, width=300, height=180, corner_radius=12)
        hint_box.pack(padx=18, pady=(0, 18))
        hint_box.insert(
            "1.0",
            "Foydalanish:\n\n"
            "1) Local saytni ishga tushiring\n"
            "2) URL kiriting\n"
            "3) Dashboarddan API token oling\n"
            "4) Start Local Scan bosing\n"
            "5) Xohlasangiz cloudga yuboring\n"
            "6) Natijani PDF qilib saqlang"
        )
        hint_box.configure(state="disabled")

        right_panel = ctk.CTkFrame(content_frame, corner_radius=18)
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.grid_rowconfigure(2, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        result_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        result_header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        result_header.grid_columnconfigure(0, weight=1)

        result_title = ctk.CTkLabel(
            result_header,
            text="Scan Results",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        result_title.grid(row=0, column=0, sticky="w")

        self.summary_label = ctk.CTkLabel(
            result_header,
            text="Topilmalar soni: 0",
            font=ctk.CTkFont(size=13)
        )
        self.summary_label.grid(row=1, column=0, sticky="w", pady=(4, 0))

        legend_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        legend_frame.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 8))

        self.legend_badge(legend_frame, "HIGH", "#dc2626").pack(side="left", padx=(0, 8))
        self.legend_badge(legend_frame, "MEDIUM", "#f59e0b").pack(side="left", padx=(0, 8))
        self.legend_badge(legend_frame, "LOW", "#2563eb").pack(side="left", padx=(0, 8))
        self.legend_badge(legend_frame, "INFO", "#6b7280").pack(side="left", padx=(0, 8))

        self.result_box = ctk.CTkTextbox(
            right_panel,
            corner_radius=14,
            font=ctk.CTkFont(size=13),
            wrap="word"
        )
        self.result_box.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.result_box.insert("1.0", "Hozircha natija yo‘q.\n")
        self.result_box.configure(state="disabled")

    def legend_badge(self, parent, text, color):
        return ctk.CTkLabel(
            parent,
            text=f"  {text}  ",
            fg_color=color,
            text_color="white",
            corner_radius=8
        )

    def toggle_token_visibility(self):
        self.show_token = not self.show_token
        if self.show_token:
            self.token_entry.configure(show="")
            self.toggle_token_btn.configure(text="Hide")
        else:
            self.token_entry.configure(show="*")
            self.toggle_token_btn.configure(text="Show")

    def set_status(self, text: str):
        self.status_label.configure(text=f"Status: {text}")

    def set_progress(self, value: float):
        self.progress.set(value)

    def set_results(self, lines, findings_count=0):
        self.result_lines = lines[:]
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")

        for line in lines:
            self.insert_colored_line(line)

        self.result_box.configure(state="disabled")
        self.summary_label.configure(text=f"Topilmalar soni: {findings_count}")

    def insert_colored_line(self, line: str):
        start_index = self.result_box.index("end-1c")

        self.result_box.insert("end", line + "\n")

        end_index = self.result_box.index("end-1c")

        if "[HIGH]" in line:
            self.result_box.tag_add("high", start_index, end_index)
        elif "[MEDIUM]" in line:
            self.result_box.tag_add("medium", start_index, end_index)
        elif "[LOW]" in line:
            self.result_box.tag_add("low", start_index, end_index)
        elif "[INFO]" in line:
            self.result_box.tag_add("info", start_index, end_index)

        self.result_box.tag_config("high", foreground="#ff6b6b")
        self.result_box.tag_config("medium", foreground="#ffd166")
        self.result_box.tag_config("low", foreground="#66b3ff")
        self.result_box.tag_config("info", foreground="#b0b7c3")

    def clear_results(self):
        self.last_result = None
        self.result_lines = []
        self.set_results(["Hozircha natija yo‘q."], findings_count=0)
        self.set_status("Ready")
        self.set_progress(0)

    def validate_target(self):
        target = self.url_entry.get().strip()
        if not target:
            messagebox.showerror("Xatolik", "Target URL kiriting.")
            return None
        return target

    def copy_results(self):
        if not self.result_lines:
            messagebox.showwarning("Ogohlantirish", "Copy qilish uchun natija yo‘q.")
            return

        text = "\n".join(self.result_lines)
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Success", "Natijalar clipboardga copy qilindi.")

    def export_pdf(self):
        if not self.result_lines:
            messagebox.showwarning("Ogohlantirish", "PDF uchun natija yo‘q.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"scan_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )

        if not file_path:
            return

        try:
            c = canvas.Canvas(file_path, pagesize=A4)
            width, height = A4

            y = height - 50
            c.setFont("Helvetica-Bold", 16)
            c.drawString(40, y, "AI Security Lab - Scan Report")

            y -= 25
            c.setFont("Helvetica", 11)
            c.drawString(40, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            target = self.url_entry.get().strip() or "-"
            y -= 20
            c.drawString(40, y, f"Target: {target}")

            y -= 30
            c.setFont("Helvetica", 10)

            for line in self.result_lines:
                if y < 50:
                    c.showPage()
                    y = height - 50
                    c.setFont("Helvetica", 10)

                safe_line = line[:120]
                c.drawString(40, y, safe_line)
                y -= 16

            c.save()
            messagebox.showinfo("Success", f"PDF saqlandi:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Xatolik", f"PDF export xatoligi:\n{e}")

    def disable_buttons(self):
        self.scan_button.configure(state="disabled")
        self.send_button.configure(state="disabled")

    def enable_buttons(self):
        self.scan_button.configure(state="normal")
        self.send_button.configure(state="normal")

    def run_scan(self):
        target = self.validate_target()
        if not target:
            self.after(0, lambda: self.set_status("Ready"))
            return

        self.after(0, self.disable_buttons)
        self.after(0, lambda: self.set_progress(0.15))
        self.after(0, lambda: self.set_status("Scanning..."))
        self.after(0, lambda: self.set_results(["Scanning boshlandi..."], findings_count=0))

        try:
            self.after(0, lambda: self.set_progress(0.45))
            result = scan_target(target, timeout=DEFAULT_TIMEOUT)
            self.last_result = result
            self.after(0, lambda: self.set_progress(0.85))

            lines = []
            findings = result.get("findings", [])

            if result.get("status") == "error":
                for item in findings:
                    sev = item.get("severity", "unknown").upper()
                    detail = item.get("detail", "No detail")
                    lines.append(f"[{sev}] {detail}")
                self.after(0, lambda: self.set_results(lines, len(findings)))
                self.after(0, lambda: self.set_progress(1))
                self.after(0, lambda: self.set_status("Scan failed"))
                return

            for i, item in enumerate(findings, start=1):
                sev = item.get("severity", "info").upper()
                ftype = item.get("type", "issue")
                detail = item.get("detail", "No detail")
                recommendation = item.get("recommendation", "No recommendation")
                lines.append(f"{i}. [{sev}] {ftype} - {detail}")
                lines.append(f"    Recommendation: {recommendation}")
                lines.append("")

            self.after(0, lambda: self.set_results(lines, len(findings)))
            self.after(0, lambda: self.set_progress(1))
            self.after(0, lambda: self.set_status("Scan completed"))

        except Exception as e:
            self.after(0, lambda: self.set_results([f"[HIGH] {str(e)}"], 1))
            self.after(0, lambda: self.set_progress(1))
            self.after(0, lambda: self.set_status("Error"))
        finally:
            self.after(0, self.enable_buttons)

    def start_scan_thread(self):
        threading.Thread(target=self.run_scan, daemon=True).start()

    def run_send(self):
        target = self.validate_target()
        if not target:
            self.after(0, lambda: self.set_status("Ready"))
            return

        api_token = self.token_entry.get().strip()
        server_url = self.server_entry.get().strip()

        if not api_token:
            messagebox.showerror("Xatolik", "API token kiriting.")
            self.after(0, lambda: self.set_status("Ready"))
            return

        if not server_url:
            messagebox.showerror("Xatolik", "Cloud server URL kiriting.")
            self.after(0, lambda: self.set_status("Ready"))
            return

        self.after(0, self.disable_buttons)
        self.after(0, lambda: self.set_status("Scanning and sending..."))
        self.after(0, lambda: self.set_progress(0.1))

        try:
            result = scan_target(target, timeout=DEFAULT_TIMEOUT)
            self.last_result = result
            self.after(0, lambda: self.set_progress(0.55))

            response = submit_scan_results(
                server_url,
                api_token,
                result["target_url"],
                result["findings"]
            )
            self.after(0, lambda: self.set_progress(0.9))

            findings = result.get("findings", [])
            lines = []

            for i, item in enumerate(findings, start=1):
                sev = item.get("severity", "info").upper()
                ftype = item.get("type", "issue")
                detail = item.get("detail", "No detail")
                recommendation = item.get("recommendation", "No recommendation")
                lines.append(f"{i}. [{sev}] {ftype} - {detail}")
                lines.append(f"    Recommendation: {recommendation}")
                lines.append("")

            lines.append("")
            lines.append("[INFO] Cloud response:")
            lines.append(f"[INFO] Status code: {response.status_code}")
            lines.append(f"[INFO] Body: {response.text}")

            self.after(0, lambda: self.set_results(lines, len(findings)))
            self.after(0, lambda: self.set_progress(1))

            if response.status_code == 200:
                self.after(0, lambda: self.set_status("Sent successfully"))
                self.after(0, lambda: messagebox.showinfo("Success", "Natija cloud serverga yuborildi."))
            else:
                self.after(0, lambda: self.set_status("Server error"))
                self.after(0, lambda: messagebox.showerror(
                    "Server xatoligi",
                    f"{response.status_code}\n{response.text}"
                ))

        except Exception as e:
            self.after(0, lambda: self.set_results([f"[HIGH] {str(e)}"], 1))
            self.after(0, lambda: self.set_progress(1))
            self.after(0, lambda: self.set_status("Error"))
            self.after(0, lambda: messagebox.showerror("Xatolik", str(e)))
        finally:
            self.after(0, self.enable_buttons)

    def send_scan_thread(self):
        threading.Thread(target=self.run_send, daemon=True).start()


if __name__ == "__main__":
    app = DesktopScannerApp()
    app.mainloop()