$env:SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
$env:SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
$env:TARGET_COUNTRY = "US"

Set-Location "C:\Users\msi\Desktop\OpenCode\spy tool project\native-ad-spy-main"

Write-Host "Starting Native Ad Spy Tool on http://localhost:3000"
py -m streamlit run app.py --server.port 3000