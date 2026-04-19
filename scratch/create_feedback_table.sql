-- 🧠 Knowledge Base: Forensic Feedback
-- This table stores manual overrides to "teach" the tool.

CREATE TABLE IF NOT EXISTS forensic_feedback (
    domain TEXT PRIMARY KEY,
    forced_type TEXT NOT NULL CHECK (forced_type IN ('Affiliate', 'Arbitrage')),
    notes TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable select access for authenticated users
ALTER TABLE forensic_feedback DISABLE ROW LEVEL SECURITY;

-- Optional: Index for fast lookup
CREATE INDEX IF NOT EXISTS idx_feedback_domain ON forensic_feedback(domain);
