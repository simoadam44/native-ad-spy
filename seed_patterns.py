import os
import sys
from supabase import create_client

# Add parent dir to path to import utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use credentials from environment or fallback to hardcoded (from your detect_affiliates.py)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://avxoumymzbioeabxfcca.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

PATTERNS = [
    # --- Tracking Tools ---
    {"pattern": "voluumtrk.com", "type": "Tracking Tool", "entity_name": "Voluum"},
    {"pattern": "clickflux.com", "type": "Tracking Tool", "entity_name": "RedTrack"},
    {"pattern": "binom.net", "type": "Tracking Tool", "entity_name": "Binom"},
    {"pattern": "bevo.media", "type": "Tracking Tool", "entity_name": "Bevo"},
    {"pattern": "funnelish.com", "type": "Tracking Tool", "entity_name": "Funnelish"},
    {"pattern": "pxlme.me", "type": "Tracking Tool", "entity_name": "PixelMe"},
    {"pattern": "trckapp.com", "type": "Tracking Tool", "entity_name": "AnyTrack"},
    {"pattern": "linktrackr.com", "type": "Tracking Tool", "entity_name": "LinkTrackr"},
    {"pattern": "tkr.me", "type": "Tracking Tool", "entity_name": "ThriveTracker"},
    {"pattern": "clickmeter.com", "type": "Tracking Tool", "entity_name": "ClickMeter"},
    {"pattern": "adsbridge.com", "type": "Tracking Tool", "entity_name": "AdsBridge"},
    
    # --- Affiliate Networks ---
    {"pattern": "go2cloud.org", "type": "Affiliate Network", "entity_name": "HasOffers (TUNE)"},
    {"pattern": "hopfeed.com", "type": "Affiliate Network", "entity_name": "System1"},
    {"pattern": "clickbank.net", "type": "Affiliate Network", "entity_name": "ClickBank"},
    {"pattern": "maxbounty.com", "type": "Affiliate Network", "entity_name": "MaxBounty"},
    {"pattern": "mb103.com", "type": "Affiliate Network", "entity_name": "MaxBounty"},
    {"pattern": "advidi.com", "type": "Affiliate Network", "entity_name": "Advidi"},
    {"pattern": "convert2media.com", "type": "Affiliate Network", "entity_name": "Convert2Media"},
    {"pattern": "adtrafico.com", "type": "Affiliate Network", "entity_name": "Adtrafico"},
    {"pattern": "everadtrk.com", "type": "Affiliate Network", "entity_name": "Everad"},
    {"pattern": "ldbt.io", "type": "Affiliate Network", "entity_name": "LeadBit"},
    {"pattern": "offervault.com", "type": "Affiliate Network", "entity_name": "OfferVault (Meta)"},
    {"pattern": "awin.com", "type": "Affiliate Network", "entity_name": "Awin"},
    {"pattern": "shareasale.com", "type": "Affiliate Network", "entity_name": "ShareASale"},
    {"pattern": "impact.com", "type": "Affiliate Network", "entity_name": "Impact"},
    {"pattern": "rakuten.com", "type": "Affiliate Network", "entity_name": "Rakuten"},
    
    # --- DSPs / Direct Redirects ---
    {"pattern": "outbrain.com/network/redir", "type": "Affiliate Network", "entity_name": "Outbrain DSP"},
    {"pattern": "taboola.com/network/redir", "type": "Affiliate Network", "entity_name": "Taboola DSP"},
]

def seed():
    print(f"Seeding {len(PATTERNS)} patterns into tracking_patterns...")
    for p in PATTERNS:
        try:
            res = supabase.table("tracking_patterns").upsert(p, on_conflict="pattern").execute()
            print(f"  [OK] {p['entity_name']} ({p['pattern']})")
        except Exception as e:
            print(f"  [ERROR] {p['entity_name']}: {e}")

if __name__ == "__main__":
    seed()
