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
    const BOGUS_DOMAINS = ["ploynest.com", "mgid.com", "adskeeper.com", "ipqualityscore.com", "bot-detected", "400-bad-request"];
    
    let currentUrl = url;
    let redirectCount = 0;
    const maxRedirects = 6;

    console.log(`[RESOLVER] Resolving: ${url} (Ref: ${referer})`);

    while (redirectCount < maxRedirects) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 7000);

      try {
        const response = await fetch(currentUrl, {
          method: "GET",
          redirect: "manual",
          signal: controller.signal,
          headers: {
            "Referer": referer,
            "User-Agent": redirectCount === 0 
              ? "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
              : "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
          },
        });

        clearTimeout(timeout);
        
        const location = response.headers.get("location");
        const status = response.status;

        if (status === 400 || status === 403) {
          console.log(`[RESOLVER] Blocked at ${currentUrl} (Status: ${status})`);
          break;
        }
        
        if (status >= 300 && status < 400 && location) {
          const nextUrl = new URL(location, currentUrl).toString();
          console.log(`[RESOLVER] Step ${redirectCount + 1}: -> ${nextUrl}`);
          
          if (BOGUS_DOMAINS.some(d => nextUrl.toLowerCase().includes(d))) {
            console.log(`[RESOLVER] Bogus hit: ${nextUrl}`);
            break; 
          }

          currentUrl = nextUrl;
          redirectCount++;
        } else {
          break;
        }
      } catch (fError: any) {
        console.error(`[RESOLVER] Fetch error at step ${redirectCount}:`, fError.message);
        break;
      }
    }

    const isBogus = BOGUS_DOMAINS.some(d => currentUrl.toLowerCase().includes(d));
    return NextResponse.json({ 
      resolved: currentUrl, 
      resolved_ok: !isBogus && currentUrl !== url,
      redirects: redirectCount
    });

  } catch (error: any) {
    console.error("[RESOLVER] Fatal Error:", error.message);
    return NextResponse.json({ resolved: url, resolved_ok: false, error: error.message });
  }
}
