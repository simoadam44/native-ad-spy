-- Affiliate Intelligence V2: Forensic Data Expansion

-- 1. New columns for enhanced extraction
ALTER TABLE ads ADD COLUMN IF NOT EXISTS traffic_source TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS widget_id TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS publisher_site TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS content_id TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS path_segments JSONB;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS tracker_id TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS needs_review BOOLEAN DEFAULT FALSE;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS network_confidence TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS tracker_confidence TEXT;

-- 2. Indexes for fast forensic analysis
CREATE INDEX IF NOT EXISTS idx_affiliate_id ON ads(affiliate_id);
CREATE INDEX IF NOT EXISTS idx_offer_id ON ads(offer_id);
CREATE INDEX IF NOT EXISTS idx_traffic_source ON ads(traffic_source);
CREATE INDEX IF NOT EXISTS idx_affiliate_network ON ads(affiliate_network);
CREATE INDEX IF NOT EXISTS idx_needs_review ON ads(needs_review);

-- 3. Migration: Flag existing affiliate ads without extraction for review
UPDATE ads SET needs_review = TRUE 
WHERE ad_type = 'Affiliate' 
AND affiliate_network IS NULL;
