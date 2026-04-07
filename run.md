# Mandera Analytics — Batch Data Pipeline

A production-grade batch analytics pipeline that generates synthetic transactional data, stores it in MongoDB Atlas, extracts into MinIO and PostgreSQL, transforms into analytics-ready staging tables, and orchestrates everything through Apache Airflow.

---

## Architecture Overview

```
GitHub Actions (8 AM & 4 PM WAT)
        │
        ▼
   MongoDB Atlas  ◄── Faker (customers, products, orders)
        │
        ├──────────────────┐
        ▼                  ▼
   MinIO (archive)    PostgreSQL (raw)
                           │
                           ▼
                     Validate & Monitor
                           │
                           ▼
                    Transform (staging)
                           │
                           ▼
                    Truncate raw tables
```

All orchestrated by **Apache Airflow** running on Docker.

---

## Prerequisites

- **Docker Desktop** — installed and running
- **MongoDB Atlas** — free-tier cluster ([create one here](https://www.mongodb.com/cloud/atlas/register))
- **Python 3.11+** — for running scripts locally (optional, Airflow handles it in Docker)
- **Git** and **GitHub CLI** (`gh`) — for version control

---

## Quick Start

### 1. Clone and Configure

```bash
git clone https://github.com/tripleaceme/mandera-batch-pipeline.git
cd mandera-batch-pipeline
cp .env.example .env
```

Edit `.env` and set your MongoDB Atlas connection string:

```
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/mandera_analytics?retryWrites=true&w=majority
```

Then generate a Fernet key for Airflow encryption:

```bash
python3 -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

Paste the output as the value for `AIRFLOW__CORE__FERNET_KEY` in your `.env` file.

> **Note:** All other values in `.env` have working defaults for local Docker. Only `MONGO_URI` and `AIRFLOW__CORE__FERNET_KEY` need to be set.

---

### 2. Start the Infrastructure

```bash
docker compose up -d
```

This starts **8 services**:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Airflow UI** | http://localhost:8080 | `admin` / `admin` |
| **MinIO Console** | http://localhost:9001 | `minioadmin` / `minioadmin123` |
| **pgAdmin** | http://localhost:5050 | No login required (desktop mode) |
| **PostgreSQL** | `localhost:5433` | `pipeline` / `pipeline_secret` |
| **Redis** | `localhost:6379` | — |

Wait about 30–60 seconds for all services to become healthy. Check status:

```bash
docker compose ps
```

All services should show `Up` (and `healthy` for postgres, minio, redis).

---

### 3. Verify Database Setup

The `db-setup` container automatically creates all schemas and tables on first startup:

- `raw.customers_raw`, `raw.products_raw`, `raw.orders_raw`
- `staging.customers_clean`, `staging.products_clean`, `staging.orders_clean`
- `monitoring.batch_log`

**To verify via pgAdmin:**

1. Open http://localhost:5050
2. In the left sidebar, expand **Mandera Warehouse** → **Schemas**
3. You should see three schemas: `raw`, `staging`, `monitoring`
4. When prompted for a password, enter: `pipeline_secret`

**To verify via command line (optional):**

```bash
docker compose exec postgres psql -U pipeline -d mandera_warehouse \
  -c "\dt raw.*; \dt staging.*; \dt monitoring.*;"
```

---

## Running the Pipeline

You can run the pipeline in two ways: **manually step-by-step** (recommended for learning) or **fully orchestrated via Airflow**.

---

### Option A: Manual Step-by-Step

Install Python dependencies locally first:

```bash
pip install -r requirements.txt
```

When running scripts locally (outside Docker), your `.env` should have:

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
MINIO_ENDPOINT=http://localhost:9000
```

> **Important:** Inside Docker, services communicate via container names (`postgres`, `minio`). Locally, you connect via `localhost` with the external ports.

#### Step 1: Generate Data → MongoDB Atlas

```bash
python -m generator.data_generator
```

Expected output:

```
  ✓ Inserted 15 customers
  ✓ Inserted 7 products
  ✓ Inserted 3421 orders

✓ Data generation complete.
```

Verify in MongoDB Atlas that the `customers`, `products`, and `orders` collections have documents. Each record includes a `batch_id` like `2026_04_07_07_batch_1`.

#### Step 2: Extract → MinIO (Archive)

```bash
python -m extraction.extract_mongo_to_minio
```

Open http://localhost:9001, log in with `minioadmin` / `minioadmin123`, and browse the `mandera-raw` bucket. You should see:

```
mandera-raw/
  customers/2026/04/07/<run_id>.json
  products/2026/04/07/<run_id>.json
  orders/2026/04/07/<run_id>.json
```

> **Note:** The bucket is created automatically on first extraction. It won't exist before you run this step.

#### Step 3: Extract → PostgreSQL Raw Tables

```bash
python -m extraction.extract_mongo_to_postgres
```

Verify in pgAdmin: navigate to **Mandera Warehouse** → **raw** → **Tables** → right-click `orders_raw` → **View/Edit Data** → **First 100 Rows**.

Or via command line:

```bash
docker compose exec postgres psql -U pipeline -d mandera_warehouse \
  -c "SELECT COUNT(*) FROM raw.orders_raw;"
```

#### Step 4: Validate Data Quality

```bash
python -m validation.validate_data_quality
```

Expected: `✓ All validation checks passed`

This checks:
- `order_id`, `customer_id`, `product_id` are not null
- `amount` is positive
- `payment_status` is one of: `paid`, `failed`, `pending`
- `batch_id` exists on all records

#### Step 5: Transform Raw → Staging

```bash
python -m transformation.transform_customers
python -m transformation.transform_products
python -m transformation.transform_orders
```

Transformations include: deduplication, null handling, type correction, and standardized naming (title case for names, lowercase for emails).

Verify in pgAdmin under **staging** schema, or:

```bash
docker compose exec postgres psql -U pipeline -d mandera_warehouse \
  -c "SELECT COUNT(*) FROM staging.orders_clean;"
```

#### Step 6: Truncate Raw Tables

```bash
python -m maintenance.truncate_raw_tables
```

This clears the raw tables after successful transformation, preparing them for the next batch.

---

### Option B: Airflow Orchestration

Once you've verified the manual steps work, let Airflow handle everything automatically.

1. Open http://localhost:8080 (login: `admin` / `admin`)
2. Find `mandera_batch_pipeline` in the DAGs list
3. Toggle it **ON**
4. Click the **play button** to trigger a manual run

The DAG runs this task graph:

```
extract_to_minio ──┐
                   ├──► log_monitoring ──► validate_quality ──┐
extract_to_postgres┘                                          │
                                          ┌───────────────────┘
                                          ├─ transform_customers ─┐
                                          ├─ transform_products   ├──► truncate_raw
                                          └─ transform_orders ────┘
```

**DAG Configuration:**
- **Schedule:** 8:30 AM & 4:30 PM WAT (30 min after data generation)
- **Retries:** 2 per task, 5-minute delay between retries
- **SLA:** 1 hour
- **Max active runs:** 1 (prevents concurrent pipeline runs)

---

## GitHub Actions (Automated Data Generation)

The `.github/workflows/generate_data.yml` workflow generates synthetic data on a cron schedule:

- **8:00 AM WAT** (07:00 UTC)
- **4:00 PM WAT** (15:00 UTC)

It can also be triggered manually via `workflow_dispatch`.

**Required GitHub Secrets:**

| Secret | Value |
|--------|-------|
| `MONGO_URI` | Your MongoDB Atlas connection string |
| `MONGO_DB` | `mandera_analytics` |

#### How to Create the Secrets

**Option A: Via GitHub UI**

1. Go to your repo on GitHub: https://github.com/tripleaceme/mandera-batch-pipeline
2. Click **Settings** (top tab bar)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. For the first secret:
   - **Name:** `MONGO_URI`
   - **Secret:** `mongodb+srv://<username>:<password>@<cluster>.mongodb.net/mandera_analytics?retryWrites=true&w=majority`
   - Click **Add secret**
6. Click **New repository secret** again
7. For the second secret:
   - **Name:** `MONGO_DB`
   - **Secret:** `mandera_analytics`
   - Click **Add secret**

**Option B: Via GitHub CLI**

```bash
# Set MONGO_URI (paste your full Atlas connection string when prompted)
gh secret set MONGO_URI

# Set MONGO_DB
gh secret set MONGO_DB --body "mandera_analytics"
```

#### How to Get Your MongoDB Atlas Connection String

1. Log in to [MongoDB Atlas](https://cloud.mongodb.com)
2. Click **Connect** on your cluster
3. Choose **Drivers**
4. Copy the connection string — it looks like:
   ```
   mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
5. Replace `<username>` and `<password>` with your Atlas database user credentials
6. Add the database name before the `?`: `.../mandera_analytics?retryWrites=true&w=majority`

#### Allow GitHub Actions to Connect to MongoDB Atlas

GitHub Actions runners use dynamic IPs, so you must whitelist all IPs in Atlas:

1. Go to [MongoDB Atlas](https://cloud.mongodb.com) → your project
2. In the left sidebar, click **Network Access** (under Security)
3. Click **Add IP Address**
4. Click **ALLOW ACCESS FROM ANYWHERE** (sets `0.0.0.0/0`)
5. Click **Confirm**

> This is safe for a learning project — Atlas still requires username/password authentication. The IP list is just an additional firewall layer.

Wait about 1 minute for the change to propagate, then test the workflow.

> **Tip:** After adding the secrets and whitelisting IPs, trigger the workflow manually to test: go to **Actions** → **Generate Synthetic Data → MongoDB Atlas** → **Run workflow**.

---

## Web UIs at a Glance

### pgAdmin (PostgreSQL)
- **URL:** http://localhost:5050
- **Purpose:** Browse schemas, query tables, inspect data
- **Pre-configured:** "Mandera Warehouse" server appears automatically in the sidebar
- **Password when prompted:** `pipeline_secret`

### MinIO Console
- **URL:** http://localhost:9001
- **Login:** `minioadmin` / `minioadmin123`
- **Purpose:** Browse archived JSON files by date partition, upload/download objects, manage buckets and access policies

### Airflow
- **URL:** http://localhost:8080
- **Login:** `admin` / `admin`
- **Purpose:** Monitor DAG runs, view task logs, trigger manual runs, track SLA

---

## Project Structure

```
batch-pipeline/
├── .github/workflows/
│   └── generate_data.yml          # GitHub Actions: scheduled data generation
├── airflow/dags/
│   └── mandera_pipeline_dag.py    # Airflow DAG orchestration
├── config/
│   ├── settings.py                # Centralized configuration (env-driven)
│   └── pgadmin_servers.json       # pgAdmin auto-connect config
├── extraction/
│   ├── extract_mongo_to_minio.py  # MongoDB → MinIO (JSON archive)
│   └── extract_mongo_to_postgres.py # MongoDB → PostgreSQL raw tables
├── generator/
│   ├── data_generator.py          # Orchestrator
│   ├── faker_customers.py         # 10-20 customers per run
│   ├── faker_products.py          # 5-10 products per run
│   └── faker_orders.py            # 2000-5000 orders per run
├── maintenance/
│   └── truncate_raw_tables.py     # Clean raw tables after transform
├── sql/
│   ├── create_raw_tables.sql      # raw schema (landing buffers)
│   ├── create_staging_tables.sql  # staging schema (cleaned data)
│   ├── create_monitoring_tables.sql # monitoring schema (observability)
│   └── truncate_raw_tables.sql    # Cleanup SQL
├── transformation/
│   ├── transform_customers.py     # Dedup, standardize, upsert
│   ├── transform_products.py
│   └── transform_orders.py
├── validation/
│   ├── validate_batch_counts.py   # Row count monitoring
│   └── validate_data_quality.py   # Data contract checks
├── docs/
│   ├── architecture.md            # System design
│   ├── data_dictionary.md         # Schema definitions
│   └── architecture-diagram.html  # Visual diagram
├── docker-compose.yml             # 8 services
├── Dockerfile                     # Airflow + dependencies
├── requirements.txt               # Python packages
└── .env.example                   # Environment template
```

---

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `MONGO_URI` | MongoDB Atlas connection string | **Required — no default** |
| `MONGO_DB` | MongoDB database name | `mandera_analytics` |
| `POSTGRES_USER` | PostgreSQL username | `pipeline` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `pipeline_secret` |
| `POSTGRES_DB` | PostgreSQL database | `mandera_warehouse` |
| `POSTGRES_HOST` | PostgreSQL host | `postgres` (Docker) / `localhost` (local) |
| `POSTGRES_PORT` | PostgreSQL port | `5432` (Docker internal) |
| `MINIO_ROOT_USER` | MinIO access key | `minioadmin` |
| `MINIO_ROOT_PASSWORD` | MinIO secret key | `minioadmin123` |
| `MINIO_ENDPOINT` | MinIO API URL | `http://minio:9000` (Docker) / `http://localhost:9000` (local) |
| `MINIO_BUCKET` | MinIO bucket name | `mandera-raw` |
| `AIRFLOW__CORE__FERNET_KEY` | Encryption key for Airflow secrets | **Required — generate one** |
| `NUMBER_OF_BATCHES` | Batches per day | `2` |

---

## Troubleshooting

**Port 5432 already in use:**
The Docker PostgreSQL maps to port **5433** externally to avoid conflicts with local PostgreSQL installations. Connect via `localhost:5433`, not `5432`.

**MinIO bucket is empty:**
The `mandera-raw` bucket is created automatically when you first run the extraction step. Run the data generator first, then the extraction.

**Airflow SQLAlchemy error:**
Ensure `requirements.txt` has `sqlalchemy>=1.4.0,<2.0.0`. Airflow 2.9.x is not compatible with SQLAlchemy 2.x.

**pgAdmin asks for a password:**
Enter `pipeline_secret` (the PostgreSQL password from your `.env`).

**GitHub Actions: SSL handshake failed / ServerSelectionTimeoutError:**
Your MongoDB Atlas cluster is blocking GitHub Actions runners. Go to Atlas → **Network Access** → **Add IP Address** → **ALLOW ACCESS FROM ANYWHERE** (`0.0.0.0/0`). See the [GitHub Actions section](#allow-github-actions-to-connect-to-mongodb-atlas) for details.

**Docker services won't start:**
Make sure Docker Desktop is running: `open -a Docker` (macOS).

---

## Teardown

```bash
# Stop all services (preserves data)
docker compose down

# Stop and delete all data (volumes)
docker compose down -v
```
