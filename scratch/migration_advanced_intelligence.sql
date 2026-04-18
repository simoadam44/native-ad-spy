-- 1. Add missing intelligence columns to the main ads table
ALTER TABLE ads ADD COLUMN IF NOT EXISTS detected_tracker TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS language TEXT;

-- 2. Expand the AI domain cache to store tracking and language intel
ALTER TABLE ai_domain_cache ADD COLUMN IF NOT EXISTS detected_tracker TEXT;
ALTER TABLE ai_domain_cache ADD COLUMN IF NOT EXISTS detected_network TEXT;
ALTER TABLE ai_domain_cache ADD COLUMN IF NOT EXISTS language TEXT;

-- Optional: Update index for better dashboard performance on filters
CREATE INDEX IF NOT EXISTS idx_ads_detected_tracker ON ads(detected_tracker);
CREATE INDEX IF NOT EXISTS idx_ads_language ON ads(language);
