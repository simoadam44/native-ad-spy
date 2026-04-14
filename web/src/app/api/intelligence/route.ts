import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

// Use server-side Supabase client (no row limit issues)
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

function extractDomain(url: string): string {
  try {
    const parsed = new URL(url);
    return parsed.hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    // Try to extract manually
    const match = url.match(/(?:https?:\/\/)?(?:www\.)?([^\/?\s]+)/i);
    return match ? match[1].toLowerCase() : url.toLowerCase();
  }
}

function normTitle(t: string): string {
  return t?.toLowerCase().trim().replace(/\s+/g, " ") ?? "";
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const landing = searchParams.get("landing") ?? "";
  const title = searchParams.get("title") ?? "";
  const currentId = searchParams.get("id") ?? "";

  if (!landing && !title) {
    return NextResponse.json({ error: "Missing params" }, { status: 400 });
  }

  const domain = extractDomain(landing);
  const normalizedTitle = normTitle(title);

  // ── 1. Same advertiser: all ads sharing the same landing domain ──
  // We search by domain in the landing column, fetch up to 500
  const { data: domainAds, error: domainErr } = await supabase
    .from("ads")
    .select("id, network, title, created_at, landing, impressions")
    .ilike("landing", `%${domain}%`)
    .neq("id", currentId)
    .order("created_at", { ascending: true })
    .limit(500);

  if (domainErr) {
    console.error("[intelligence] domain query error:", domainErr);
  }

  const advertiserAds = domainAds ?? [];

  // Unique networks across all their ads
  const networks: string[] = [...new Set(
    advertiserAds.map((a) => a.network).filter(Boolean)
  )];

  // All unique titles this advertiser uses
  const titlesSet = new Set<string>();
  advertiserAds.forEach((a) => {
    if (a.title) titlesSet.add(a.title.trim());
  });
  const titles = [...titlesSet];

  // Days since first ever ad for this advertiser
  const allDates = advertiserAds
    .map((a) => new Date(a.created_at).getTime())
    .filter((t) => !isNaN(t));
  const firstSeenTs = allDates.length > 0 ? Math.min(...allDates) : Date.now();
  const daysSinceFirst = Math.round((Date.now() - firstSeenTs) / (1000 * 60 * 60 * 24));

  // ── 2. Cross-network: same title across different networks ──
  // Search by exact title in DB (case insensitive)
  const { data: titleAds, error: titleErr } = await supabase
    .from("ads")
    .select("id, network, title, created_at, impressions")
    .ilike("title", title.trim())
    .neq("id", currentId)
    .limit(200);

  if (titleErr) {
    console.error("[intelligence] title query error:", titleErr);
  }

  const sameTitle = titleAds ?? [];

  // Also check partial/fuzzy matches from domain ads
  const fuzzyTitleMatches = advertiserAds.filter((a) => {
    const at = normTitle(a.title);
    return (
      at === normalizedTitle ||
      (at.length > 10 && normalizedTitle.length > 10 &&
        (at.includes(normalizedTitle.slice(0, 20)) ||
          normalizedTitle.includes(at.slice(0, 20))))
    );
  });

  // Combine exact + fuzzy
  const allTitleMatchIds = new Set([...sameTitle.map((a) => a.id), ...fuzzyTitleMatches.map((a) => a.id)]);
  const crossNetworkAds = [
    ...sameTitle,
    ...fuzzyTitleMatches.filter((a) => !sameTitle.find((s) => s.id === a.id)),
  ];

  const crossNetworks: string[] = [...new Set(
    crossNetworkAds.map((a) => a.network).filter(Boolean)
  )];
  const isCrossNetwork = crossNetworks.length > 1;

  // ── 3. Return structured response ──
  return NextResponse.json({
    domain,
    // Publisher strategy
    networks,
    titles,
    daysSinceFirst,
    totalAds: advertiserAds.length,
    // Cross-network
    isCrossNetwork,
    crossNetworks,
    crossNetworkAds: crossNetworkAds.slice(0, 10).map((a) => ({
      id: a.id,
      network: a.network,
      title: a.title,
      impressions: a.impressions,
    })),
    // Recent ads from same advertiser (latest 5)
    recentAds: [...advertiserAds]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 5)
      .map((a) => ({
        id: a.id,
        network: a.network,
        title: a.title?.slice(0, 60),
        impressions: a.impressions,
      })),
  });
}
