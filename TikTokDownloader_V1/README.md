# TikTok Downloader V1

## For development

Install Python 3.10+ on the developer machine, then:

```powershell
py -m pip install -r requirements.txt
py app.py
```

## Build the Windows EXE

On Windows, double-click `build_windows.bat`, or run:

```powershell
py -m pip install --upgrade yt-dlp pyinstaller
py -m PyInstaller --noconfirm --clean --onefile --windowed --name TikTokDownloader app.py
```

The finished application will be:

```text
dist\TikTokDownloader.exe
```

The end user only needs that EXE. They do not need Python or yt-dlp installed separately.

## V1 behavior

- Accepts a public TikTok profile URL.
- Looks at the first N profile entries, default 10.
- Downloads the selected public videos.
- Saves them to the user's Downloads\TikTokDownloads folder by default.
- Uses upload date + TikTok video ID for filenames.
- Shows basic progress/status.
- Continues when an individual video fails.

## Notes

TikTok can change its website behavior, and third-party downloading may stop working until yt-dlp is updated. Use the application only for content you are authorized to save and in accordance with TikTok's terms and applicable law.
