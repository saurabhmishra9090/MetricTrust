
-- MetricTrust: Synthetic KPI definition-change test
-- This is a simulated change, not an official NYC definition change.

BEGIN TRANSACTION;

-- Close Version 1 on the day before Version 2 becomes effective.
UPDATE metric_registry
SET
    effective_to = DATE '2025-12-31',
    is_current = FALSE
WHERE metric_id = 'CLOSURE_RATE'
  AND version = 1;

-- Register Version 2 without overwriting Version 1.
INSERT INTO metric_registry (
    metric_id,
    metric_name,
    metric_description,
    formula_definition,
    aggregation_grain,
    version,
    effective_from,
    effective_to,
    is_current,
    change_reason
)
VALUES (
    'CLOSURE_RATE',
    'Request Closure Rate',
    'Synthetic test: requests with a non-null closure date divided by all requests in the creation-month cohort.',
    'Requests with closed_date IS NOT NULL / all requests in the cohort * 100',
    'Request creation month',
    2,
    DATE '2026-01-01',
    NULL,
    TRUE,
    'SYNTHETIC TEST: changed closure criterion from status = Closed to closed_date IS NOT NULL'
)
ON CONFLICT (metric_id, version) DO NOTHING;

COMMIT;

-- Verify version history.
SELECT
    metric_id,
    version,
    formula_definition,
    effective_from,
    effective_to,
    is_current,
    change_reason
FROM metric_registry
WHERE metric_id = 'CLOSURE_RATE'
ORDER BY version;
