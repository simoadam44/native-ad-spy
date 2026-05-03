import sys

file_path = r'c:\Users\msi\Desktop\ia project\p3\native-ad-spy-main\utils\lp_analyzer.py'
with open(file_path, 'r', encoding='utf8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if line.startswith('async def click_cta_and_capture(page, ad_type: str = "Affiliate") -> dict:'):
        start_idx = i
        break

if start_idx != -1:
    for i in range(start_idx + 1, len(lines)):
        if lines[i].startswith('async def analyze_page_structure'):
            end_idx = i
            break

if start_idx != -1 and end_idx != -1:
    new_func = '''async def click_cta_and_capture(page, ad_type: str = "Affiliate") -> dict:
    """
    Clicks the CTA button and captures the full redirect chain.
    Enhanced with Deep Navigation to bypass cloaking.
    """
    from utils.deep_navigator import find_real_offer_deep
    
    # Extract title if available, otherwise empty
    try:
        title = await page.title()
    except Exception:
        title = ""
        
    deep_result = await find_real_offer_deep(
        page=page,
        landing_url=page.url,
        ad_title=title
    )
    
    final_offer_url = deep_result.get("final_url")
    redirect_chain = deep_result.get("clean_chain", [])
    
    return {
        "cta_found": deep_result.get("success", False),
        "cta_text": deep_result.get("cta_text", "Unknown"),
        "final_offer_url": final_offer_url,
        "redirect_chain": redirect_chain
    }

'''
    
    lines = lines[:start_idx] + [new_func] + lines[end_idx:]
    with open(file_path, 'w', encoding='utf8') as f:
        f.writelines(lines)
    print('Successfully replaced click_cta_and_capture.')
else:
    print('Could not find function bounds.')
