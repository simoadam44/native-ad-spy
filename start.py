import os
import sys

os.environ['SUPABASE_URL'] = 'https://avxoumymzbioeabxfcca.supabase.co'
os.environ['SUPABASE_KEY'] = 'sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX'
os.environ['TARGET_COUNTRY'] = 'US'

os.chdir(r"C:\Users\msi\Desktop\OpenCode\spy tool project\native-ad-spy-main")
os.system('py -m streamlit run app.py --server.port 3000 --server.headless true')