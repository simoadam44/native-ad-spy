@echo off
chcp 65001 >nul
cd /d "%~dp0"

set SUPABASE_URL=https://avxoumymzbioeabxfcca.supabase.co
set SUPABASE_KEY=sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX
set TARGET_COUNTRY=US
set ANTHROPIC_API_KEY=

echo Starting Native Ad Spy Tool...
echo.

py -m streamlit run app.py --server.port 3000 --server.headless=true --browser.gatherUsageStats=false