@echo off
echo Closing any existing Chrome instances...
taskkill /F /IM chrome.exe /T 2>nul
echo Launching Chrome in Debug Mode (Port 9222)...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
echo Done! Chrome is now ready for the crawler.
pause
