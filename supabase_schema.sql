-- 1. Upgrade the ads table with intelligence columns
ALTER TABLE ads ADD COLUMN IF NOT EXISTS ad_type TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS page_subtype TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS affiliate_id TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS offer_id TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS sub_id TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS final_offer_url TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS detected_network TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS cta_text TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS has_countdown BOOLEAN DEFAULT FALSE;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS has_video BOOLEAN DEFAULT FALSE;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS price_found TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS lp_screenshot_url TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS offer_screenshot_url TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS cloaking_type TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS deep_analyzed_at TIMESTAMP;

-- 2. Logs table for debugging analysis steps
CREATE TABLE IF NOT EXISTS analysis_logs (
  id BIGSERIAL PRIMARY KEY,
  ad_id UUID REFERENCES ads(id) ON DELETE CASCADE,
  step TEXT,
  error_message TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Advanced View: Advertiser profiles based on affiliate patterns
CREATE OR REPLACE VIEW advertiser_profiles AS
SELECT
  affiliate_id,
  detected_network,
  COUNT(*) as total_ads,
  COUNT(DISTINCT offer_id) as unique_offers,
  SUM(COALESCE(impressions, 0)) as total_impressions,
  MAX(last_seen) as last_active,
  array_agg(DISTINCT network) as native_networks,
  array_agg(DISTINCT cloaking_type) as cloaking_methods,
  (
    SELECT cta_text 
    FROM ads a2 
    WHERE a2.affiliate_id = ads.affiliate_id 
    GROUP BY cta_text 
    ORDER BY COUNT(*) DESC 
    LIMIT 1
  ) as top_cta_text
FROM ads
WHERE affiliate_id IS NOT NULL 
  AND affiliate_id <> ''
  AND affiliate_id <> 'Direct / Unknown'
GROUP BY affiliate_id, detected_network
ORDER BY total_impressions DESC;

-- Enable RLS permissions if needed (assuming public access for now as per current setup)
ALTER TABLE analysis_logs DISABLE ROW LEVEL SECURITY;
