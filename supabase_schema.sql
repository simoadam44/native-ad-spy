-- Native Ad Spy: Affiliate Intelligence Schema

-- 1. Upgrade the ads table with comprehensive forensic columns
ALTER TABLE ads ADD COLUMN IF NOT EXISTS classification_score INTEGER DEFAULT 0;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS classification_confidence TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS deep_analyzed_at TIMESTAMP;

-- Technical Offer Details
ALTER TABLE ads ADD COLUMN IF NOT EXISTS final_offer_url TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS offer_domain TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS offer_vertical TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS affiliate_network TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS tracker_tool TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS offer_id TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS affiliate_id TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS sub_id TEXT;

-- Interaction Results
ALTER TABLE ads ADD COLUMN IF NOT EXISTS cta_found BOOLEAN DEFAULT FALSE;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS cta_text TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS redirect_chain_json TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS all_params_json TEXT;

-- Visual Evidence
ALTER TABLE ads ADD COLUMN IF NOT EXISTS lp_screenshot_url TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS offer_screenshot_url TEXT;

-- Metadata/Detection
ALTER TABLE ads ADD COLUMN IF NOT EXISTS page_subtype TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS language TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS has_countdown BOOLEAN DEFAULT FALSE;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS has_video BOOLEAN DEFAULT FALSE;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS cloaking_type TEXT;


-- 2. Views for Intelligence Analysis
DROP VIEW IF EXISTS advertiser_profiles;
DROP VIEW IF EXISTS offer_intelligence;

-- View: Advertiser Profiles
-- Groups intelligence by Affiliate ID to show competitor blueprints
CREATE OR REPLACE VIEW advertiser_profiles AS
SELECT
    affiliate_id,
    affiliate_network,
    tracker_tool,
    offer_vertical,
    COUNT(*)                              AS total_ads,
    COUNT(DISTINCT offer_id)              AS unique_offers,
    COUNT(DISTINCT offer_domain)          AS unique_products,
    SUM(COALESCE(impressions, 0))         AS total_impressions,
    MAX(last_seen)                        AS last_active,
    MIN(created_at)                       AS first_seen,
    array_agg(DISTINCT network)           AS native_networks
FROM ads
WHERE affiliate_id IS NOT NULL 
  AND affiliate_id <> ''
  AND affiliate_id <> 'Direct / Unknown'
GROUP BY affiliate_id, affiliate_network, tracker_tool, offer_vertical
ORDER BY total_impressions DESC;


-- 3. View: Offer Intelligence
-- Groups data by Offer ID to show which products are scaling
CREATE OR REPLACE VIEW offer_intelligence AS
SELECT
    offer_id,
    offer_domain,
    offer_vertical,
    affiliate_network,
    COUNT(DISTINCT affiliate_id)          AS total_affiliates,
    COUNT(*)                              AS total_ads,
    SUM(COALESCE(impressions, 0))         AS total_impressions,
    MAX(last_seen)                        AS last_active,
    array_agg(DISTINCT network)           AS native_networks,
    array_agg(DISTINCT tracker_tool)      AS trackers_used
FROM ads
WHERE offer_id IS NOT NULL
  AND offer_id <> ''
GROUP BY offer_id, offer_domain, offer_vertical, affiliate_network
ORDER BY total_impressions DESC;


-- 4. Logs Table for Tracking Deep Analysis Steps
CREATE TABLE IF NOT EXISTS analysis_logs (
  id BIGSERIAL PRIMARY KEY,
  ad_id UUID REFERENCES ads(id) ON DELETE CASCADE,
  step TEXT,
  error_message TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Security
ALTER TABLE analysis_logs DISABLE ROW LEVEL SECURITY;
