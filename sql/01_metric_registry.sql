
-- MetricTrust: KPI Registry
-- Purpose: Maintain versioned KPI definitions.

CREATE TABLE IF NOT EXISTS metric_registry (
    metric_id VARCHAR NOT NULL,
    metric_name VARCHAR NOT NULL,
    metric_description VARCHAR,
    formula_definition VARCHAR NOT NULL,
    aggregation_grain VARCHAR NOT NULL,
    version INTEGER NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_current BOOLEAN NOT NULL,
    change_reason VARCHAR,
    PRIMARY KEY (metric_id, version)
);

-- Reconciliation rules are stored separately from KPIs.

CREATE TABLE IF NOT EXISTS reconciliation_rule_registry (
    rule_id VARCHAR PRIMARY KEY,
    rule_name VARCHAR NOT NULL,
    rule_description VARCHAR NOT NULL,
    severity VARCHAR NOT NULL,
    version INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL
);

-- KPI 1: Count of distinct service requests.
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
    'REQ_COUNT',
    'Total Service Requests',
    'Number of distinct NYC 311 request IDs.',
    'COUNT(DISTINCT unique_key)',
    'Calendar month',
    1,
    DATE '2023-01-01',
    NULL,
    TRUE,
    'Initial MetricTrust definition'
);

-- KPI 2: Closure rate.
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
    'Percentage of requests in the selected cohort that have a closed status.',
    'Closed-status requests / all requests in the cohort * 100',
    'Request creation month',
    1,
    DATE '2023-01-01',
    NULL,
    TRUE,
    'Initial MetricTrust definition'
);

-- Rule MT-001: Closed status must have a closure date.
INSERT INTO reconciliation_rule_registry (
    rule_id,
    rule_name,
    rule_description,
    severity,
    version,
    is_active
)
VALUES (
    'MT-001',
    'Closed Request Missing Closure Date',
    'Flag records where status is Closed and closed_date is missing.',
    'High',
    1,
    TRUE
);
