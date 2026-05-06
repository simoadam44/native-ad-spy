-- Run this in your Supabase SQL Editor to synchronize the schema
-- and eliminate "Removing unsupported column" warnings.

-- 1. Support for Cloudflare detection status
ALTER TABLE ads ADD COLUMN IF NOT EXISTS cloudflare_blocked BOOLEAN DEFAULT FALSE;

-- 2. Support for Smart Offer Validation details
ALTER TABLE ads ADD COLUMN IF NOT EXISTS offer_type_detail TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS offer_type_confidence TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS validation_retries INTEGER DEFAULT 0;

-- 3. Support for Tech Stack analysis (Wappalyzer)
ALTER TABLE ads ADD COLUMN IF NOT EXISTS tech_stack TEXT[] DEFAULT '{}';
ALTER TABLE ads ADD COLUMN IF NOT EXISTS cms TEXT;

-- 4. Support for hidden endpoints found by LinkFinder
ALTER TABLE ads ADD COLUMN IF NOT EXISTS hidden_endpoints_found TEXT[] DEFAULT '{}';

-- 5. Support for tracking software detection
ALTER TABLE ads ADD COLUMN IF NOT EXISTS tracking_software TEXT[] DEFAULT '{}';

-- 6. Analysis Logs Update (if needed)
ALTER TABLE analysis_logs ADD COLUMN IF NOT EXISTS severity TEXT DEFAULT 'info';
