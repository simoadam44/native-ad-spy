-- ══════════════════════════════════════════════════════
-- MIGRATION: Fix Affiliate/Arbitrage False Positives
-- Target: Ads where redirect chain contains Ad-Tech only
-- ══════════════════════════════════════════════════════

-- Add classification_reason if not exists
ALTER TABLE ads ADD COLUMN IF NOT EXISTS classification_reason TEXT;

-- Move clear ad-tech noise chains to Arbitrage
UPDATE ads 
SET ad_type = 'Arbitrage',
    classification_confidence = 'high',
    classification_reason = 'Bulk fix: Ad-tech noise detected in redirect chain (taboola_hm, rubicon, etc.)',
    needs_review = FALSE,
    deep_analyzed_at = NOW()
WHERE ad_type = 'Affiliate'
AND (
  redirect_chain_json ILIKE '%taboola_hm=%'
  OR redirect_chain_json ILIKE '%rubiconproject%'
  OR redirect_chain_json ILIKE '%gdpr_consent=%'
  OR redirect_chain_json ILIKE '%deepintent%'
  OR redirect_chain_json ILIKE '%prebid%'
  OR redirect_chain_json ILIKE '%usersync%'
  OR redirect_chain_json ILIKE '%match.adsrvr.org%'
);

-- Reset analytics fields for these changed ads
UPDATE ads
SET affiliate_network = NULL,
    tracker_tool = 'No Tracker',
    affiliate_id = NULL,
    offer_id = NULL,
    final_offer_url = landing
WHERE classification_reason = 'Bulk fix: Ad-tech noise detected in redirect chain (taboola_hm, rubicon, etc.)';
