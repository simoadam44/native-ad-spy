import os
import re
from urllib.parse import urlparse, parse_qs
from supabase import create_client

# Load environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://avxoumymzbioeabxfcca.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Static Parameter Patterns (Fallback) ---
PARAMETER_TRACKERS = {
    r"[?&]cid=": "Voluum / RedTrack",
    r"[?&]clickid=": "Generic Tracker",
    r"[?&]subid=": "Binom / Generic",
    r"[?&]pixel=": "Custom Tracker",
    r"[?&]aff_id=": "Generic Affiliate",
    r"[?&]affid=": "Generic Affiliate",
    r"[?&]offer_id=": "Generic Affiliate",
}

class AdvancedDetector:
    def __init__(self):
        self.patterns = []
        self._load_patterns()

    def _load_patterns(self):
        """Loads patterns from Supabase tracking_patterns table."""
        try:
            res = supabase.table("tracking_patterns").select("*").execute()
            self.patterns = res.data if res.data else []
        except Exception as e:
            print(f"Error loading tracking patterns: {e}")
            self.patterns = []

    def analyze_chain(self, redirect_chain: list[str]) -> dict:
        """
        Analyzes a full redirect chain and returns detected metadata.
        Returns: { "affiliate_network": str, "tracking_tool": str }
        """
        results = {
            "affiliate_network": "Direct / Private",
            "tracking_tool": "Direct / Unknown"
        }
        
        if not redirect_chain:
            return results

        # Process each URL in the chain (Ad link -> Tracker -> Network -> Landing)
        for url in redirect_chain:
            url_lower = url.lower()
            
            # 1. Match against DB Patterns
            for p in self.patterns:
                pattern = p['pattern'].lower()
                if pattern in url_lower:
                    if p['type'] == 'Tracking Tool':
                        results["tracking_tool"] = p['entity_name']
                    elif p['type'] == 'Affiliate Network':
                        results["affiliate_network"] = p['entity_name']

            # 2. Parameter-based detection (if tracker still unknown)
            if results["tracking_tool"] == "Direct / Unknown":
                for regex, name in PARAMETER_TRACKERS.items():
                    if re.search(regex, url_lower):
                        results["tracking_tool"] = name
                        break

        return results

# Singleton instance
detector = AdvancedDetector()

def detect_from_chain(chain: list[str]) -> dict:
    return detector.analyze_chain(chain)
