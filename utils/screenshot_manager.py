import os
from datetime import datetime
from supabase import create_client

# Supabase Credentials
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://avxoumymzbioeabxfcca.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def get_db_client():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)

async def take_and_store_screenshot(page, ad_id: str, screenshot_type: str) -> str:
    """
    Captures a screenshot of the current page and uploads it to Supabase Storage.
    Returns the public URL of the uploaded image.
    """
    supabase = get_db_client()
    if not supabase:
        return None

    try:
        # 1. Take Screenshot
        # We use jpeg and lower quality to keep file sizes manageable
        screenshot_bytes = await page.screenshot(
            full_page=False, 
            type="jpeg", 
            quality=75
        )

        # 2. Generate Path
        date_prefix = datetime.now().strftime("%Y/%m")
        filename = f"{date_prefix}/{ad_id}_{screenshot_type}.jpg"
        bucket_name = "ad-screenshots"

        # 3. Upload to Supabase Storage
        try:
            supabase.storage.from_(bucket_name).upload(
                path=filename,
                file=screenshot_bytes,
                file_options={"content-type": "image/jpeg", "upsert": "true"}
            )
        except Exception as upload_err:
            # If bucket doesn't exist or other error, log it
            print(f"Storage Upload Error: {upload_err}")
            return None

        # 4. Get Public URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(filename)
        
        # 5. Update ads table
        column_name = "lp_screenshot_url" if screenshot_type == "landing_page" else "offer_screenshot_url"
        supabase.table("ads").update({column_name: public_url}).eq("id", ad_id).execute()
        
        return public_url

    except Exception as e:
        print(f"Screenshot Error for {ad_id}: {e}")
        return None

def setup_storage_bucket():
    """Run once to ensure the bucket is ready."""
    supabase = get_db_client()
    if not supabase: return
    try:
        supabase.storage.create_bucket("ad-screenshots", options={"public": True})
        print("Bucket 'ad-screenshots' created/verified.")
    except:
        pass # Already exists

if __name__ == "__main__":
    # Test bucket setup
    setup_storage_bucket()
