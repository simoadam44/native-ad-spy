-- Forensic Intelligence Expansion V2
-- This migration adds deeper tracking for native sources and affiliate forensics.

-- 1. Add Forensic Columns
ALTER TABLE ads ADD COLUMN IF NOT EXISTS traffic_source TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS widget_id TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS publisher_site TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS content_id TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS path_segments JSONB;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS tracker_id TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS needs_review BOOLEAN DEFAULT FALSE;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS network_confidence TEXT DEFAULT 'low';
ALTER TABLE ads ADD COLUMN IF NOT EXISTS tracker_confidence TEXT DEFAULT 'low';
ALTER TABLE ads ADD COLUMN IF NOT EXISTS classification_reason TEXT;

-- 2. Create Forensic Indexes
CREATE INDEX IF NOT EXISTS idx_affiliate_id ON ads(affiliate_id);
CREATE INDEX IF NOT EXISTS idx_offer_id ON ads(offer_id);
CREATE INDEX IF NOT EXISTS idx_traffic_source ON ads(traffic_source);
CREATE INDEX IF NOT EXISTS idx_affiliate_network ON ads(affiliate_network);
CREATE INDEX IF NOT EXISTS idx_needs_review ON ads(needs_review) WHERE needs_review = TRUE;

-- 3. Initial Migration for existing data
-- Flag ads that might be missing data for manual review
UPDATE ads 
SET needs_review = TRUE 
WHERE ad_type = 'Affiliate' 
  AND (affiliate_network IS NULL OR affiliate_network = 'No Network Detected');
