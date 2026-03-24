import asyncio
import os
import importlib.util
import sys

# Provide dummy env vars for initialization
os.environ["SUPABASE_URL"] = "https://example.supabase.co"
os.environ["SUPABASE_KEY"] = "dummy-key"

# Mock Supabase
class MockSupabase:
    def table(self, name):
        return self
    def select(self, *args):
        return self
    def eq(self, *args):
        return self
    def execute(self):
        class Result:
            def __init__(self):
                self.data = []
        return Result()
    def update(self, *args):
        return self
    def insert(self, *args):
        return self

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

async def test_crawler(name, path):
    print(f"\n--- Testing {name} ---")
    module = load_module(name, path)
    # Patch supabase
    module.supabase = MockSupabase()
    
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Test only the first target to save time
        target = module.MGID_TARGETS[0] if name == "mgid" else module.OUTBRAIN_TARGETS[0]
        if name == "mgid":
            await module.scrape_mgid(browser, target)
        else:
            await module.scrape_outbrain(browser, target)
        await browser.close()

async def main():
    # Only test one of each for quick verification
    try:
        await test_crawler("mgid", "mgid_crawler.py")
    except Exception as e:
        print(f"MGID Test failed: {str(e).encode('ascii', 'ignore').decode('ascii')}")
        
    try:
        await test_crawler("outbrain", "outbrain_crawler.py")
    except Exception as e:
        print(f"Outbrain Test failed: {str(e).encode('ascii', 'ignore').decode('ascii')}")

if __name__ == "__main__":
    asyncio.run(main())
