import os
import json
from urllib.parse import urlparse
from groq import Groq
from supabase import create_client

# Groq Setup with Rotation support
GROQ_KEYS = [
    os.environ.get("GROQ_API_KEY"),
    os.environ.get("GROQ_API_KEY_SECONDARY")
]
# Filter out None values and initialize clients
groq_clients = [Groq(api_key=k, timeout=60.0) for k in GROQ_KEYS if k]

def get_groq_completion(messages, response_format={"type": "json_object"}):
    """
    Helper to try completions across multiple API keys if one fails.
    """
    for client in groq_clients:
        try:
            return client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.0,
                response_format=response_format
            )
        except Exception as e:
            print(f"⚠️ Groq client error: {e}. Trying next key if available...")
            continue
    return None

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
    Role: Identify if this URL/Page is 'Arbitrage' or 'Affiliate'.
    You are a digital marketing forensic analyst.
    
    Strict Logic:
    1. If the URL contains paging patterns like '/2', '/3', 'page/', or the title is a celebrity/lifestyle listicle -> Categorize as 'Arbitrage'.
    2. If the page lacks a clear 'Buy/Order Now' or 'Order' button for a specific physical/digital product -> Categorize as 'Arbitrage'.
    3. If the page is an article about general topics (Health tips, Celebs, Travel) and surrounded by Ad units (Taboola, Outbrain) -> Categorize as 'Arbitrage'.
    4. Only categorize as 'Affiliate' if there is a clear CTA to a sales page or a branded product checkout.

    You MUST respond with a valid JSON object:
    {
      "decision": {
        "target_url": "identified target offer URL or null",
        "ad_type": "Arbitrage" | "Affiliate",
        "funnel_type": "VSL" | "Advertorial" | "Quiz" | "Direct Sales" | "Article",
        "cloaking_detected": boolean,
        "confidence_score": 0.0 to 1.0,
        "detected_tracker": "string or null",
        "detected_network": "string or null",
        "language": "ISO code"
      },
      "reasoning": "Explicit reason (e.g., pagination detected, listicle format, no product CTA)"
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
    
    # 3. Groq Request with Retries and Rotation
    parsed_json = None
    completion = get_groq_completion([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ])
    
    if completion:
        try:
            response_str = completion.choices[0].message.content
            parsed_json = json.loads(response_str)
        except Exception as e:
            print(f"JSON Parsing Error: {e}")

    # 4. Save to Cache and Return
    if parsed_json and "decision" in parsed_json:
        dec = parsed_json["decision"]
        try:
            supabase.table("ai_domain_cache").upsert({
                "domain": domain,
                "target_url": dec.get("target_url"),
                "ad_type": dec.get("ad_type"),
                "funnel_type": dec.get("funnel_type"),
                "cloaking_detected": dec.get("cloaking_detected"),
                "confidence_score": dec.get("confidence_score"),
                "detected_tracker": dec.get("detected_tracker"),
                "detected_network": dec.get("detected_network"),
                "language": dec.get("language"),
                "reasoning": parsed_json.get("reasoning", "")
            }).execute()
        except Exception as e:
            print(f"⚠️ Cache write error: {e}")
        return parsed_json

    # Final fallback if Groq completely fails
    return {
        "decision": {"ad_type": "Unknown", "confidence_score": 0.0},
        "reasoning": "Groq AI failed after 3 attempts."
    }

def find_cta_selector(links_data: list, text_content: str) -> dict:
    """
    Identifies the best CTA selector for an affiliate offer using Groq.
    """
    system_prompt = """
    Role: Affiliate CTA Discovery Agent.
    Task: Identify the CSS selector or Text for the primary 'Bridge-to-Offer' button.
    Data: A list of links/buttons found on the page.
    
    Priority:
    - Text like 'Buy', 'Order', 'Get Discount', 'Claim', 'Haz clic aquí'.
    - Links with parameters (?prod=, ?aff=, etc).
    - Links leading to a different domain.
    
    Output ONLY JSON:
    {
      "step": "click_cta",
      "selector_type": "text | css | xpath",
      "target_selector": "the specific value",
      "scroll_required": true,
      "wait_after_click_ms": 5000,
      "reasoning": "why this button?"
    }
    """
    try:
        completion = get_groq_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Links and Buttons: {json.dumps(links_data[:50])}\nPage Context: {text_content[:800]}"}
        ])
        if completion:
            return json.loads(completion.choices[0].message.content)
    except:
        return None

def dissect_tracking_link(final_url: str) -> dict:
    """
    Performs forensic analysis of an affiliate redirect link using Groq.
    """
    system_prompt = """
    Role: Affiliate Tracking Forensic Analyst.
    Task: Extract Network and Tracker Tool from a final offer URL.

    Logic:
    - Look for parameters like 'net', 'affid', 'oid', 'clickid'.
    - Map 'net=1673' or similar to Private Networks.
    - Identify Voluum, Binom, Keitaro, Keitaro patterns in URL structure.
    
    Output ONLY JSON:
    {
      "intelligence": {
        "detected_network": "Name or ID",
        "tracker_tool": "Voluum/Binom/Keitaro/Unknown",
        "parameters": { "name": "value" },
        "is_direct_link": boolean
      },
      "reasoning": "explanation"
    }
    """
    try:
        completion = get_groq_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Final URL: {final_url}"}
        ])
        if completion:
            return json.loads(completion.choices[0].message.content)
    except:
        return None
