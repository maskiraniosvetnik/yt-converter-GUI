import os
import re
import shlex
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


APP_NAME = "YT2MP4 USB Converter"


def safe_filename(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]+", "-", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:180] or "video"


class ConverterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("760x520")
        self.root.minsize(680, 450)

        self.url_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(Path.home() / "Videos"))
        self.quality_var = tk.StringVar(value="best")
        self.status_var = tk.StringVar(value="Ready")

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 12, "pady": 8}

        title = ttk.Label(self.root, text=APP_NAME, font=("Arial", 18, "bold"))
        title.pack(anchor="w", **pad)

        note = ttk.Label(
            self.root,
            text="Paste a video URL, choose a folder, and convert/download as MP4. Use only where you have permission.",
            wraplength=720,
        )
        note.pack(anchor="w", padx=12)

        frm = ttk.Frame(self.root)
        frm.pack(fill="x", **pad)

        ttk.Label(frm, text="Video URL:").grid(row=0, column=0, sticky="w")
        url_entry = ttk.Entry(frm, textvariable=self.url_var)
        url_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=4)

        ttk.Label(frm, text="Save to:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        out_entry = ttk.Entry(frm, textvariable=self.output_var)
        out_entry.grid(row=3, column=0, sticky="ew", pady=4)

        browse = ttk.Button(frm, text="Browse", command=self.choose_folder)
        browse.grid(row=3, column=1, padx=(8, 0), pady=4)

        ttk.Label(frm, text="Quality:").grid(row=4, column=0, sticky="w", pady=(10, 0))
        quality = ttk.Combobox(
            frm,
            textvariable=self.quality_var,
            values=[
                "best",
                "1080p",
                "720p",
                "480p",
                "audio-only-mp3",
            ],
            state="readonly",
            width=18,
        )
        quality.grid(row=5, column=0, sticky="w", pady=4)

        frm.columnconfigure(0, weight=1)

        btns = ttk.Frame(self.root)
        btns.pack(fill="x", padx=12, pady=4)

        self.start_btn = ttk.Button(btns, text="Download / Convert to MP4", command=self.start_download)
        self.start_btn.pack(side="left")

        ttk.Button(btns, text="Open Output Folder", command=self.open_folder).pack(side="left", padx=8)

        status = ttk.Label(self.root, textvariable=self.status_var)
        status.pack(anchor="w", padx=12, pady=(8, 0))

        self.log = tk.Text(self.root, height=15, wrap="word")
        self.log.pack(fill="both", expand=True, padx=12, pady=8)
        self.log.insert("end", "Log will appear here.\n")

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_var.get())
        if folder:
            self.output_var.set(folder)

    def open_folder(self):
        folder = self.output_var.get().strip()
        if folder:
            subprocess.Popen(["xdg-open", folder])

    def log_line(self, text: str):
        self.log.insert("end", text + "\n")
        self.log.see("end")

    def check_dependencies(self):
        missing = []
        for cmd in ["yt-dlp", "ffmpeg"]:
            if subprocess.call(["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
                missing.append(cmd)
        return missing

    def build_command(self, url: str, out_dir: Path):
        quality = self.quality_var.get()

        output_template = str(out_dir / "%(title).180s.%(ext)s")

        if quality == "audio-only-mp3":
            return [
                "yt-dlp",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "-o", str(out_dir / "%(title).180s.%(ext)s"),
                url,
            ]

        if quality == "1080p":
            fmt = "bv*[height<=1080]+ba/b[height<=1080]/best[height<=1080]"
        elif quality == "720p":
            fmt = "bv*[height<=720]+ba/b[height<=720]/best[height<=720]"
        elif quality == "480p":
            fmt = "bv*[height<=480]+ba/b[height<=480]/best[height<=480]"
        else:
            fmt = "bv*+ba/best"

        return [
            "yt-dlp",
            "-f", fmt,
            "--merge-output-format", "mp4",
            "--recode-video", "mp4",
            "--embed-metadata",
            "--embed-thumbnail",
            "--convert-thumbnails", "jpg",
            "-o", output_template,
            url,
        ]

    def start_download(self):
        url = self.url_var.get().strip()
        out_dir = Path(self.output_var.get().strip()).expanduser()

        if not url:
            messagebox.showerror(APP_NAME, "Paste a URL first.")
            return

        missing = self.check_dependencies()
        if missing:
            messagebox.showerror(
                APP_NAME,
                "Missing dependency: " + ", ".join(missing) +
                "\n\nInstall with:\nsudo apt install yt-dlp ffmpeg",
            )
            return

        out_dir.mkdir(parents=True, exist_ok=True)

        self.start_btn.config(state="disabled")
        self.status_var.set("Working...")
        self.log_line("")
        self.log_line("Starting download/conversion...")
        self.log_line(f"URL: {url}")
        self.log_line(f"Output: {out_dir}")

        thread = threading.Thread(target=self.run_download, args=(url, out_dir), daemon=True)
        thread.start()

    def run_download(self, url: str, out_dir: Path):
        cmd = self.build_command(url, out_dir)

        self.root.after(0, self.log_line, "Command: " + " ".join(shlex.quote(c) for c in cmd))

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            assert process.stdout is not None
            for line in process.stdout:
                self.root.after(0, self.log_line, line.rstrip())

            code = process.wait()

            if code == 0:
                self.root.after(0, self.status_var.set, "Done")
                self.root.after(0, self.log_line, "Finished successfully.")
            else:
                self.root.after(0, self.status_var.set, "Failed")
                self.root.after(0, self.log_line, f"Process exited with code {code}.")

        except Exception as exc:
            self.root.after(0, self.status_var.set, "Error")
            self.root.after(0, self.log_line, f"Error: {exc}")

        finally:
            self.root.after(0, self.start_btn.config, {"state": "normal"})


def main():
    root = tk.Tk()
    try:
        root.call("source", "/usr/share/themes/Adwaita/gtk-3.0/gtk-contained.css")
    except Exception:
        pass
    app = ConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
