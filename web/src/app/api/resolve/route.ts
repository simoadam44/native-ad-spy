import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const url = request.nextUrl.searchParams.get("url");
  const referer = request.nextUrl.searchParams.get("ref") || "https://brainberries.co/";

  if (!url) {
    return NextResponse.json({ error: "No URL provided" }, { status: 400 });
  }

  // Only resolve MGID/AdsKeeper tracking links
  const isTrackingLink =
    url.includes("clck.mgid.com") || url.includes("clck.adskeeper.com");

  if (!isTrackingLink) {
    return NextResponse.json({ resolved: url });
  }

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);

    const response = await fetch(url, {
      method: "GET",
      redirect: "follow",
      signal: controller.signal,
      headers: {
        Referer: referer,
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        Accept:
          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
      },
    });

    clearTimeout(timeout);

    const finalUrl = response.url;

    // Reject if still on MGID (bot detected) or ploynest spam
    const BOGUS = ["ploynest.com", "mgid.com", "adskeeper.com"];
    const isBogus = BOGUS.some((d) => finalUrl.includes(d));

    if (isBogus || finalUrl === url) {
      return NextResponse.json({ resolved: url, resolved_ok: false });
    }

    return NextResponse.json({ resolved: finalUrl, resolved_ok: true });
  } catch {
    return NextResponse.json({ resolved: url, resolved_ok: false });
  }
}
