-- Migration: Add JSON artifact columns for regeneration support
-- Date: 2026-01-27
-- Description: Store BasicReport and RiskBrief as JSON for file regeneration

-- Add basic_report_json column
ALTER TABLE construction_reports
ADD COLUMN IF NOT EXISTS basic_report_json JSONB;

-- Add risk_brief_json column
ALTER TABLE construction_reports
ADD COLUMN IF NOT EXISTS risk_brief_json JSONB;

-- Add comment for documentation
COMMENT ON COLUMN construction_reports.basic_report_json IS 'BasicReport JSON for tasks.xlsx and report.docx regeneration';
COMMENT ON COLUMN construction_reports.risk_brief_json IS 'RiskBrief JSON for risk_brief.pdf regeneration';
