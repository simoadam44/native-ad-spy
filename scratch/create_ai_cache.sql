-- Execute this in the Supabase SQL Editor
CREATE TABLE IF NOT EXISTS ai_domain_cache (
  id BIGSERIAL PRIMARY KEY,
  domain TEXT UNIQUE NOT NULL,
  target_url TEXT,
  ad_type TEXT,
  funnel_type TEXT,
  cloaking_detected BOOLEAN,
  confidence_score NUMERIC,
  reasoning TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Optional: For fast lookups
CREATE INDEX IF NOT EXISTS idx_ai_domain_cache_domain ON ai_domain_cache(domain);
