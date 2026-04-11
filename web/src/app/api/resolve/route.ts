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
    const BOGUS_DOMAINS = [
      "ploynest.com", "mgid.com", "adskeeper.com", "ipqualityscore.com", 
      "bot-detected", "400-bad-request", "403-forbidden", 
      "cookielaw.org", "onetrust.com", "cookieconsent",
      "adtrafficquality.google", "googleadservices.com", "activeview", "sodar"
    ];
    
    let currentUrl = url;
    let redirectCount = 0;
    const maxRedirects = 8; // Increased for complex chains

    console.log(`[RESOLVER] Resolving: ${url} (Ref: ${referer})`);

    while (redirectCount < maxRedirects) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 8000);

      try {
        const response = await fetch(currentUrl, {
          method: "GET",
          redirect: "manual",
          signal: controller.signal,
          headers: {
            "Referer": referer,
            "User-Agent": redirectCount % 2 === 0 
              ? "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
              : "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
          },
        });

        clearTimeout(timeout);
        
        const status = response.status;
        const location = response.headers.get("location");

        // 1. Handle HTTP Redirects
        if (status >= 300 && status < 400 && location) {
          const nextUrl = new URL(location, currentUrl).toString();
          console.log(`[RESOLVER] Step ${redirectCount + 1} (HTTP): -> ${nextUrl}`);
          
          if (BOGUS_DOMAINS.some(d => nextUrl.toLowerCase().includes(d))) {
            console.log(`[RESOLVER] Bogus hit (HTTP): ${nextUrl}`);
            break; 
          }

          currentUrl = nextUrl;
          redirectCount++;
          continue;
        }

        // 2. Handle Meta Refresh (only for status 200)
        if (status === 200) {
          const contentType = response.headers.get("content-type") || "";
          if (contentType.includes("text/html")) {
            const html = await response.text();
            
            // Regex to find <meta http-equiv="refresh" content="...url=...">
            const metaMatch = html.match(/<meta\s+http-equiv=["']refresh["']\s+content=["'][^"']*?url=([^"']*?)["']/i);
            if (metaMatch && metaMatch[1]) {
              const nextUrl = new URL(metaMatch[1], currentUrl).toString();
              console.log(`[RESOLVER] Step ${redirectCount + 1} (Meta): -> ${nextUrl}`);
              
              if (BOGUS_DOMAINS.some(d => nextUrl.toLowerCase().includes(d))) {
                console.log(`[RESOLVER] Bogus hit (Meta): ${nextUrl}`);
                break;
              }
              
              currentUrl = nextUrl;
              redirectCount++;
              continue;
            }
          }
        }
        
        // No more redirects found
        break;

      } catch (fError: any) {
        console.error(`[RESOLVER] Fetch error at step ${redirectCount}:`, fError.message);
        break;
      }
    }

    const isBogus = BOGUS_DOMAINS.some(d => currentUrl.toLowerCase().includes(d));
    let finalUrl = currentUrl;
    
    // Check for valid hostname (must contain a dot)
    try {
      const parsedUrl = new URL(finalUrl);
      if (!parsedUrl.hostname.includes('.')) {
        finalUrl = url; // Fallback to original if completely invalid
      }
    } catch {
      finalUrl = url;
    }

    return NextResponse.json({ 
      resolved: finalUrl, 
      resolved_ok: !isBogus && finalUrl !== url && finalUrl === currentUrl,
      redirects: redirectCount
    });

  } catch (error: any) {
    console.error("[RESOLVER] Fatal Error:", error.message);
    return NextResponse.json({ resolved: url, resolved_ok: false, error: error.message });
  }
}
