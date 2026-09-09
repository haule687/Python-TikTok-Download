import os
import re
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp


APP_TITLE = "TikTok Video Downloader"
DEFAULT_COUNT = 10


class TikTokDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("620x430")
        self.root.minsize(620, 430)

        self.events = queue.Queue()
        self.downloading = False
        self.output_dir = os.path.join(os.path.expanduser("~"), "Downloads", "TikTokDownloads")

        self.url_var = tk.StringVar()
        self.count_var = tk.StringVar(value=str(DEFAULT_COUNT))
        self.folder_var = tk.StringVar(value=self.output_dir)
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)

        self._build_ui()
        self.root.after(100, self._process_events)

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=24)
        main.pack(fill="both", expand=True)

        ttk.Label(
            main, text=APP_TITLE, font=("Segoe UI", 20, "bold")
        ).pack(anchor="w", pady=(0, 20))

        ttk.Label(main, text="TikTok Profile URL").pack(anchor="w")
        url_frame = ttk.Frame(main)
        url_frame.pack(fill="x", pady=(6, 16))

        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var)
        self.url_entry.pack(side="left", fill="x", expand=True)
        self.url_entry.focus_set()

        ttk.Label(main, text="Number of newest videos").pack(anchor="w")
        self.count_entry = ttk.Spinbox(
            main, from_=1, to=100, textvariable=self.count_var, width=8
        )
        self.count_entry.pack(anchor="w", pady=(6, 16))

        ttk.Label(main, text="Save folder").pack(anchor="w")
        folder_frame = ttk.Frame(main)
        folder_frame.pack(fill="x", pady=(6, 18))

        ttk.Entry(
            folder_frame, textvariable=self.folder_var, state="readonly"
        ).pack(side="left", fill="x", expand=True)

        self.browse_button = ttk.Button(
            folder_frame, text="Browse...", command=self.choose_folder
        )
        self.browse_button.pack(side="left", padx=(8, 0))

        self.download_button = ttk.Button(
            main, text="Download Videos", command=self.start_download
        )
        self.download_button.pack(fill="x", ipady=6)

        ttk.Label(main, textvariable=self.status_var).pack(
            anchor="w", pady=(20, 6)
        )

        self.progress = ttk.Progressbar(
            main, variable=self.progress_var, maximum=100
        )
        self.progress.pack(fill="x")

        ttk.Label(
            main,
            text="Downloads are limited to publicly accessible content.",
            foreground="gray",
        ).pack(anchor="w", pady=(12, 0))

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_dir)
        if folder:
            self.output_dir = folder
            self.folder_var.set(folder)

    @staticmethod
    def validate_profile_url(url):
        pattern = r"^https?://(www\.)?tiktok\.com/@[^/?#]+/?$"
        return re.match(pattern, url.strip()) is not None

    def start_download(self):
        if self.downloading:
            return

        url = self.url_var.get().strip()

        try:
            count = int(self.count_var.get())
        except ValueError:
            messagebox.showerror("Invalid number", "Enter a whole number.")
            return

        if not self.validate_profile_url(url):
            messagebox.showerror(
                "Invalid TikTok URL",
                "Enter a TikTok profile URL such as:\n"
                "https://www.tiktok.com/@username",
            )
            return

        if not 1 <= count <= 100:
            messagebox.showerror(
                "Invalid number", "Choose between 1 and 100 videos."
            )
            return

        os.makedirs(self.output_dir, exist_ok=True)

        self.downloading = True
        self.download_button.config(state="disabled")
        self.browse_button.config(state="disabled")
        self.url_entry.config(state="disabled")
        self.count_entry.config(state="disabled")
        self.progress_var.set(0)
        self.status_var.set("Finding newest videos...")

        threading.Thread(
            target=self._download_worker,
            args=(url, count, self.output_dir),
            daemon=True,
        ).start()

    def _download_worker(self, url, count, output_dir):
        try:
            # Extract the profile's entries without downloading.
            extract_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "playlistend": count,
            }

            with yt_dlp.YoutubeDL(extract_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            entries = [e for e in (info.get("entries") or []) if e]

            if not entries:
                raise RuntimeError(
                    "No public videos were found on this profile."
                )

            # The profile feed is normally newest-first. We still request
            # only the first N entries and preserve that order.
            entries = entries[:count]
            total = len(entries)

            self.events.put(("status", f"Found {total} videos. Starting downloads..."))

            def progress_hook(d):
                if d["status"] == "downloading":
                    downloaded = d.get("downloaded_bytes", 0)
                    total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")

                    if total_bytes:
                        percent = downloaded / total_bytes * 100
                        self.events.put(("item_progress", percent))
                elif d["status"] == "finished":
                    self.events.put(("item_progress", 100))

            download_opts = {
                # Prefer MP4-compatible formats. If the best video+audio
                # streams require merging, yt-dlp will merge to MP4.
                "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
                "outtmpl": os.path.join(
                    output_dir, "%(upload_date)s_%(id)s.%(ext)s"
                ),
                "merge_output_format": "mp4",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "ignoreerrors": True,
                "progress_hooks": [progress_hook],
            }

            completed = 0

            with yt_dlp.YoutubeDL(download_opts) as ydl:
                for index, entry in enumerate(entries, start=1):
                    video_url = entry.get("webpage_url") or entry.get("url")

                    if not video_url:
                        self.events.put(
                            ("status", f"[{index}/{total}] Skipped: no video URL")
                        )
                        continue

                    title = entry.get("title") or "TikTok video"
                    self.events.put(
                        ("status", f"[{index}/{total}] {title}")
                    )
                    self.events.put(("item_progress", 0))

                    try:
                        ydl.download([video_url])
                        completed += 1
                    except Exception as exc:
                        self.events.put(
                            ("log", f"Skipped video {index}: {exc}")
                        )

                    overall = index / total * 100
                    self.events.put(("overall_progress", overall))

            self.events.put(
                (
                    "done",
                    f"Finished. Downloaded {completed} of {total} videos.\n"
                    f"Saved to: {output_dir}",
                )
            )

        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]

                if kind == "status":
                    self.status_var.set(event[1])
                elif kind == "item_progress":
                    self.progress_var.set(event[1])
                elif kind == "overall_progress":
                    self.progress_var.set(event[1])
                elif kind == "log":
                    print(event[1])
                elif kind == "done":
                    self._finish()
                    messagebox.showinfo("Download complete", event[1])
                elif kind == "error":
                    self._finish()
                    messagebox.showerror("Download failed", event[1])
        except queue.Empty:
            pass

        self.root.after(100, self._process_events)

    def _finish(self):
        self.downloading = False
        self.download_button.config(state="normal")
        self.browse_button.config(state="normal")
        self.url_entry.config(state="normal")
        self.count_entry.config(state="normal")
        self.status_var.set("Ready")


def main():
    root = tk.Tk()

    try:
        # Use a modern ttk theme when available.
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass

    TikTokDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
