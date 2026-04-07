# Architecture — Mandera Analytics Batch Pipeline

## System Overview

```
GitHub Actions (8AM & 4PM WAT)          Apache Airflow (8:30AM & 4:30PM WAT)
┌──────────────────────┐                ┌─────────────────────────────────────┐
│  generator/          │                │                                     │
│  ├─ faker_customers  │   MongoDB      │  extract_to_minio ──┐              │
│  ├─ faker_products   │──→ Atlas ──────│──                    ├→ log_monitoring
│  └─ faker_orders     │                │  extract_to_postgres ┘      │       │
│                      │                │                         validate    │
│  data_generator.py   │                │                             │       │
│  (orchestrator)      │                │  ┌─ transform_customers ─┐  │       │
└──────────────────────┘                │  ├─ transform_products  ─┼←─┘       │
                                        │  └─ transform_orders   ─┘           │
                                        │            │                        │
                                        │     truncate_raw_tables             │
                                        └─────────────────────────────────────┘
```

## Data Flow

1. **Source Generation** (GitHub Actions)
   - Faker generates customers (10-20), products (5-10), orders (2000-5000)
   - Records tagged with `batch_id` (e.g., `2026_03_23_07_batch_1`)
   - Inserted into MongoDB Atlas collections

2. **Extraction** (Airflow — parallel)
   - **MinIO**: All MongoDB records → JSON files at `{collection}/{YYYY/MM/DD}/{run_id}.json`
   - **PostgreSQL**: Same records → raw landing tables (`raw.customers_raw`, etc.)

3. **Monitoring** (Airflow)
   - Compares source_rows vs loaded_rows per table
   - Logs variance to `monitoring.batch_log`

4. **Validation** (Airflow)
   - Checks: non-null PKs, positive amounts, valid payment statuses, batch_id exists

5. **Transformation** (Airflow — parallel)
   - Deduplication, null handling, type correction, string standardization
   - Upserts into staging tables (`staging.customers_clean`, etc.)

6. **Cleanup** (Airflow)
   - Truncates all raw tables after successful transformation

## Infrastructure

| Service | Purpose | Port |
|---------|---------|------|
| PostgreSQL 16 | Warehouse (raw/staging/monitoring) + Airflow metadata | 5433 (external) |
| pgAdmin 4 | PostgreSQL web UI for browsing schemas and querying data | 5050 |
| MinIO | S3-compatible object storage (durable archive) | 9000 (API), 9001 (Console) |
| Redis 7 | Airflow Celery broker | 6379 |
| Airflow 2.9 | Pipeline orchestration (webserver, scheduler, worker) | 8080 |

## Key Design Decisions

- **Generation decoupled from processing**: Source system (GitHub Actions) runs independently from analytics pipeline (Airflow)
- **Dual-write extraction**: MinIO for archival/replay, Postgres raw for transformation
- **Raw tables as stateless buffer**: Truncated after each transform — no stale data accumulation
- **batch_id is source metadata only**: Pipeline scripts don't filter by it — they process everything in raw
- **SQL separated from Python**: DDL lives in `sql/` files, executed by Python scripts
