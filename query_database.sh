#!/bin/bash

JOB_ID=$1

# As argument $1 pass the name of the benchmark in the format benchmark_########## (ex: ./query_database.sh benchmark_1762561467)
# You can find it in the logs folder ending with .log

sqlite3 metrics.db << EOF
-- Summary statistics
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
    AVG(request_duration) as avg_duration,
    MIN(request_duration) as min_duration,
    MAX(request_duration) as max_duration
FROM metrics
WHERE benchmark_id = '${JOB_ID}';

-- Requests by client
SELECT 
    client_id,
    COUNT(*) as requests,
    AVG(request_duration) as avg_duration
FROM metrics
WHERE benchmark_id = '${JOB_ID}'
GROUP BY client_id;

-- Error distribution
SELECT 
    status_code,
    COUNT(*) as count
FROM metrics
WHERE benchmark_id = '${JOB_ID}'
  AND success = 0
GROUP BY status_code;
EOF
