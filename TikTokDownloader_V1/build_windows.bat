@echo off
setlocal

echo Installing/updating build dependencies...
py -m pip install --upgrade yt-dlp pyinstaller

echo.
echo Building TikTokDownloader.exe...
py -m PyInstaller --noconfirm --clean --onefile --windowed --name TikTokDownloader app.py

echo.
echo Build complete.
echo Your application is:
echo dist\TikTokDownloader.exe
pause
