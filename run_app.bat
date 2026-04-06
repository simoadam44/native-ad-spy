@echo off
cd /d "C:\Users\msi\Desktop\OpenCode\spy tool project\native-ad-spy-main"
set SUPABASE_URL=https://avxoumymzbioeabxfcca.supabase.co
set SUPABASE_KEY=sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX
set TARGET_COUNTRY=US
echo Starting Native Ad Spy Tool...
py -m streamlit run app.py --server.port 3000 --server.headless true