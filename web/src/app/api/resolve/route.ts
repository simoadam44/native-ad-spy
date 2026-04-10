import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const url = request.nextUrl.searchParams.get("url");
  let referer = request.nextUrl.searchParams.get("ref") || "https://brainberries.co/";

  if (!url) {
    return NextResponse.json({ error: "No URL provided" }, { status: 400 });
  }

  // Only resolve tracking links
  const isTrackingLink =
    url.includes("clck.mgid.com") || 
    url.includes("clck.adskeeper.com") || 
    url.includes("trc.taboola.com") || 
    url.includes("outbrain.com/network/redir");

  if (!isTrackingLink) {
    return NextResponse.json({ resolved: url });
  }

  console.log(`[RESOLVER] Starting resolution for: ${url} (Referer: ${referer})`);

  try {
    const BOGUS_DOMAINS = ["ploynest.com", "mgid.com", "adskeeper.com", "ipqualityscore.com", "bot-detected"];
    
    let currentUrl = url;
    let redirectCount = 0;
    const maxRedirects = 5;

    // We manually follow redirects to have better control and visibility
    while (redirectCount < maxRedirects) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 6000);

      const response = await fetch(currentUrl, {
        method: "GET",
        redirect: "manual", // Manually handle to inspect each step
        signal: controller.signal,
        headers: {
          "Referer": referer,
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
          "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
          "Accept-Language": "en-US,en;q=0.9",
        },
      });

      clearTimeout(timeout);
      
      const location = response.headers.get("location");
      
      if (response.status >= 300 && response.status < 400 && location) {
        // Build absolute URL if location is relative
        const nextUrl = new URL(location, currentUrl).toString();
        console.log(`[RESOLVER] Redirect ${redirectCount + 1}: ${currentUrl} -> ${nextUrl}`);
        
        // Stop if we hit a known bogus domain at any step
        if (BOGUS_DOMAINS.some(d => nextUrl.toLowerCase().includes(d))) {
          console.log(`[RESOLVER] Target hit bogus domain: ${nextUrl}`);
          break; 
        }

        currentUrl = nextUrl;
        redirectCount++;
      } else {
        // No more redirects
        break;
      }
    }

    const isBogus = BOGUS_DOMAINS.some(d => currentUrl.toLowerCase().includes(d));
    
    console.log(`[RESOLVER] Final Resolved URL: ${currentUrl} (Bogus: ${isBogus})`);

    return NextResponse.json({ 
      resolved: currentUrl, 
      resolved_ok: !isBogus && currentUrl !== url,
      redirects: redirectCount
    });

  } catch (error: any) {
    console.error("[RESOLVER] Error:", error.message);
    return NextResponse.json({ 
      resolved: url, 
      resolved_ok: false, 
      error: error.message 
    });
  }
}
