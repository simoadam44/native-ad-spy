import asyncio
import os
from supabase import create_client
from deep_analyzer import deep_analyze_ad

# Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://avxoumymzbioeabxfcca.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def test_learning_system():
    test_domain = "joehoft.com"
    ad_id = "test-learning-id"
    
    print(f"--- Step 1: Teaching the tool that {test_domain} is Arbitrage ---")
    supabase.table("forensic_feedback").upsert({
        "domain": test_domain,
        "forced_type": "Arbitrage",
        "notes": "Verified Arbitrage site via manual teaching"
    }).execute()
    
    print(f"\n--- Step 2: Running Deep Analysis on an ad from {test_domain} ---")
    # This should trigger the Knowledge Base Override
    result = await deep_analyze_ad(ad_id, f"https://{test_domain}/article-123", "Test Mock Ad")
    
    print(f"\n--- Step 3: Verified Result ---")
    print(f"Ad Type: {result.get('ad_type')}")
    print(f"Reason: {result.get('classification_reason')}")
    
    if result.get('classification_reason') == 'knowledge_base_override':
        print("\n✅ SUCCESS: The tool successfully used the knowledge base!")
    else:
        print("\n❌ FAILURE: The tool did not use the knowledge base.")

if __name__ == "__main__":
    asyncio.run(test_learning_system())
