# Mandera Analytics — Batch Data Pipeline

A batch data engineering pipeline that generates synthetic transactional data, stores it in MongoDB Atlas, extracts into MinIO and PostgreSQL, transforms into analytics-ready staging tables, and orchestrates everything through Apache Airflow.

## Architecture

```
GitHub Actions (cron)                 Airflow DAG (Docker)
┌────────────────────┐               ┌──────────────────────────────────────┐
│                    │               │                                      │
│  Python + Faker    │   MongoDB     │  extract_to_minio ──┐               │
│  ├─ customers      │──► Atlas ────►│                     ├► log_monitoring│
│  ├─ products       │               │  extract_to_postgres┘       │       │
│  └─ orders         │               │                         validate     │
│                    │               │                             │        │
└────────────────────┘               │  transform_* (parallel) ◄──┘        │
                                     │         │                           │
                                     │  truncate_raw_tables                │
                                     └──────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Data Generation | Python, Faker |
| Source Storage | MongoDB Atlas |
| Object Storage | MinIO (S3-compatible) |
| Data Warehouse | PostgreSQL 16 |
| Transformation | Pandas |
| Orchestration | Apache Airflow 2.9 |
| Scheduling | GitHub Actions |
| Infrastructure | Docker Compose |

## Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Airflow UI | http://localhost:8080 | `admin` / `admin` |
| MinIO Console | http://localhost:9001 | `minioadmin` / `minioadmin123` |
| pgAdmin | http://localhost:5050 | No login required |
| PostgreSQL | localhost:5433 | `pipeline` / `pipeline_secret` |

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/tripleaceme/mandera-batch-pipeline.git
cd mandera-batch-pipeline
cp .env.example .env
# Edit .env — set MONGO_URI and generate AIRFLOW__CORE__FERNET_KEY

# 2. Start infrastructure
docker compose up -d

# 3. Check all services are healthy
docker compose ps
```

See [run.md](run.md) for the complete setup guide, step-by-step pipeline execution, GitHub Actions configuration, and troubleshooting.

## Pipeline Stages

1. **Generate** — Faker creates synthetic customers, products, and orders with batch IDs
2. **Store** — Records are inserted into MongoDB Atlas collections
3. **Extract** — Dual-write to MinIO (date-partitioned JSON archive) and PostgreSQL raw tables
4. **Monitor** — Row counts and variance logged to `monitoring.batch_log`
5. **Validate** — Data contract checks (non-null IDs, positive amounts, valid payment statuses)
6. **Transform** — Deduplicate, clean nulls, standardize naming → staging tables
7. **Truncate** — Clear raw tables after successful transformation

## Project Structure

```
├── generator/           # Faker data generation scripts
├── extraction/          # MongoDB → MinIO + PostgreSQL
├── transformation/      # Raw → staging (Pandas)
├── validation/          # Data quality and contract checks
├── maintenance/         # Raw table truncation
├── airflow/dags/        # Airflow DAG definition
├── sql/                 # DDL for raw, staging, monitoring schemas
├── config/              # Centralized settings + pgAdmin config
├── docs/                # Architecture docs and data dictionary
├── .github/workflows/   # GitHub Actions for scheduled generation
├── docker-compose.yml   # 8 services (Postgres, MinIO, pgAdmin, Redis, Airflow x3, db-setup)
├── Dockerfile           # Airflow + Python dependencies
├── requirements.txt     # Python packages
├── run.md               # Detailed setup and execution guide
└── .env.example         # Environment variable template
```

## Documentation

- [run.md](run.md) — Complete setup and execution guide
- [docs/architecture.md](docs/architecture.md) — System design and data flow
- [docs/data_dictionary.md](docs/data_dictionary.md) — Schema definitions for all tables
