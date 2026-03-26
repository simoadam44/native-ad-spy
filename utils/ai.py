import anthropic
import os
import json
import streamlit as st

# --- 1. إعداد الـ API ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# --- 2. محرك التحليل (Analysis Engine) ---
def analyze_ad(title, network):
    if not ANTHROPIC_API_KEY:
        return {"error": "AI Key not configured."}
    
    prompt = f"""
    You are an expert Native Advertising Analyst.
    Analyze this ad and return ONLY a JSON response:
    Target Ad Title: "{title}"
    Network: {network}
    
    JSON format:
    {{
        "hook": "Psychological hook used (e.g. Scarcity, Curiosity)",
        "angle": "Marketing angle (e.g. Life-saving, Money-saving)",
        "audience": "Broad target audience description",
        "cta_type": "Soft vs Hard sell",
        "score": "Out of 10",
        "tip": "How to improve it"
    }}
    """
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        # استخراج الـ JSON من الرد (في حال وجود نصوص إضافية)
        content = response.content[0].text
        start = content.find('{')
        end = content.rfind('}') + 1
        return json.loads(content[start:end])
    except Exception as e:
        return {"error": f"AI Error: {str(e)}"}

# --- 3. محرك توليد العناوين (Headline Generator) ---
def generate_similar(title):
    prompt = f"""
    Based on the following winning native ad headline, generate 3 highly clickable variations that maintain the same psychological trigger but use different wording.
    
    Original Headline: "{title}"
    
    Return as a JSON list: ["Header 1", "Header 2", "Header 3"]
    """
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.content[0].text
        start = content.find('[')
        end = content.rfind(']') + 1
        return json.loads(content[start:end])
    except:
        return ["Headline 1 Alternative", "Headline 2 Alternative", "Headline 3 Alternative"]

# --- 4. تقرير النيتش (Niche Report) ---
def niche_report(network):
    prompt = f"""
    Analyze the current trends in {network} native ads. 
    Provide a marketing report in JSON format:
    {{
        "top_hooks": ["Hook1", "Hook2"],
        "dominant_angle": "Description",
        "pattern": "Observed creative pattern",
        "recommendation": "Expert advice for advertisers"
    }}
    """
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.content[0].text
        start = content.find('{')
        end = content.rfind('}') + 1
        return json.loads(content[start:end])
    except:
        return {"error": "Niche analysis unavailable."}
