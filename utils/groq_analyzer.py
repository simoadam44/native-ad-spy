import os
import json
from urllib.parse import urlparse
from groq import Groq
from supabase import create_client

# Fallback Groq Setup
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY, timeout=60.0)

# Supabase Setup for Cache
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://avxoumymzbioeabxfcca.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def invoke_groq_intelligence(title: str, landing_url: str, text_snippet: str, extracted_links: list) -> dict:
    """
    Invokes Groq API (llama-3.1-8b-instant) using strict JSON format
    to analyze the funnel logic when regex rules fail.
    Checks Supabase cache first to save tokens.
    """
    
    domain = urlparse(landing_url).netloc.lower()
    
    # 1. Check Cache
    try:
        cache_resp = supabase.table("ai_domain_cache").select("*").eq("domain", domain).execute()
        if cache_resp.data:
            print(f"✅ Found cached AI intelligence for domain: {domain}")
            item = cache_resp.data[0]
            return {
                "decision": {
                    "target_url": item.get("target_url"),
                    "ad_type": item.get("ad_type"),
                    "funnel_type": item.get("funnel_type"),
                    "cloaking_detected": item.get("cloaking_detected"),
                    "confidence_score": item.get("confidence_score"),
                    "detected_tracker": item.get("detected_tracker"),
                    "detected_network": item.get("detected_network"),
                    "language": item.get("language")
                },
                "reasoning": item.get("reasoning", "Loaded from cache")
            }
    except Exception as e:
        print(f"⚠️ Cache read error: {e}")

    # 2. Prepare Groq Request
    
    # Cap inputs to save tokens
    safe_text = text_snippet[:1200]
    safe_links = extracted_links[:30] # Top 30 links
    
    system_prompt = """
    You are a digital marketing expert specializing in uncovering affiliate funnels and tracking links.
    Your task is to analyze the landing page snippet and the extracted links to find the Final Offer target URL.
    
    Prioritize links with: hop, click, lptoken, checkout, order, track.
    Ignore: privacy, terms, contact, about, social media links.
    
    Ad Types: "Affiliate" (Focuses on buying a product) OR "Arbitrage" (Focuses on articles, top 10 lists, viral stories).
    Note: Domains like herbeauty.co, sportpirate.com, tradingblvd.com, brainberries.co are almost ALWAYS Arbitrage story sites.
    Funnel Types: "VSL", "Advertorial", "Quiz", or "Direct Sales".
    Cloaking: Set cloaking_detected to true if the landing page domain acts like a news site but links point to e-com product checkouts.
    Tracker Tools: Identify tools like Voluum, Binom, Keitaro, RedTrack, etc.
    Affiliate Networks: Identify networks like ClickBank, BuyGoods, Everflow, GiddyUp, etc.
    Language: Detect the primary language code (e.g., "en", "ar", "es").

    You MUST respond with a valid JSON object matching exactly this structure:
    {
      "decision": {
        "target_url": "best matching URL or null",
        "ad_type": "string",
        "funnel_type": "string",
        "cloaking_detected": boolean,
        "confidence_score": 0.0 to 1.0 float,
        "detected_tracker": "string or null",
        "detected_network": "string or null",
        "language": "string (ISO code)"
      },
      "reasoning": "Brief explanation"
    }
    """
    
    user_prompt = f"""
    Analyze this Data:
    Ad Title: {title}
    Landing URL: {landing_url}
    
    Page Text Snippet:
    {safe_text}
    
    Extracted Links:
    {safe_links}
    """
    
    # 3. Groq Request with Retries
    parsed_json = None
    for attempt in range(3):
        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                  {"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            response_str = completion.choices[0].message.content
            parsed_json = json.loads(response_str)
            break # Success
        except Exception as e:
            print(f"Groq Attempt {attempt+1} failed: {e}")
            if attempt < 2:
                # Wait briefly before retry
                import time
                time.sleep(2 * (attempt + 1))
    # Final fallback if Groq completely fails
    return {
        "decision": {
            "target_url": None,
            "ad_type": "Unknown",
            "funnel_type": None,
            "cloaking_detected": False,
            "confidence_score": 0.0,
            "detected_tracker": None,
            "detected_network": None,
            "language": "en"
        },
        "reasoning": "Groq AI failed after 3 attempts."
    }
