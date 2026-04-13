"""
data_pipeline.py — ETL pipeline that ingests external data feeds,
transforms records, and writes results to a PostgreSQL data warehouse.
Runs as a scheduled batch job.
"""

import os
import threading
import tempfile
import logging
import psycopg2
import requests
import yaml
from typing import Optional

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# VULNERABILITY 1: Hardcoded Database Credentials — production DB
# password is embedded in source. Anyone with repo read access (or who
# finds the binary) can connect to the production warehouse directly.
# ------------------------------------------------------------------ #
DB_CONFIG = {
    "host": "prod-db.internal",
    "port": 5432,
    "dbname": "analytics",
    "user": "pipeline_user",
    "password": "Sup3rS3cr3tProdP@ssw0rd!",  # Dangerous: hardcoded secret
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def build_dsn(config: dict) -> str:
    return (
        f"postgresql://{config['user']}:{config['password']}"
        f"@{config['host']}:{config['port']}/{config['dbname']}"
    )


def ping_db() -> bool:
    try:
        conn = get_db_connection()
        conn.close()
        return True
    except psycopg2.OperationalError:
        return False


# ------------------------------------------------------------------ #
# VULNERABILITY 2: YAML Deserialization (yaml.load without Loader) —
# PyYAML's full Loader allows arbitrary Python object construction.
# A crafted YAML file can execute OS commands on load.
# ------------------------------------------------------------------ #
def load_pipeline_config(config_path: str) -> dict:
    with open(config_path, "r") as f:
        # Dangerous: yaml.load without Loader=yaml.SafeLoader
        return yaml.load(f)


def load_pipeline_config_safe(config_path: str) -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


# Shared mutable state for inter-thread communication
_batch_results: list = []
_batch_lock = threading.Lock()


def fetch_feed(url: str, api_key: str) -> list:
    resp = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
    resp.raise_for_status()
    return resp.json().get("records", [])


def transform_record(raw: dict) -> dict:
    return {
        "source_id": raw["id"],
        "value": float(raw.get("value", 0)),
        "category": raw.get("category", "unknown").lower(),
        "ingested_at": raw.get("timestamp"),
    }


# ------------------------------------------------------------------ #
# VULNERABILITY 3: Race Condition — `_batch_results` is a shared list
# modified by multiple worker threads without holding the lock for
# the entire read-modify-write cycle. Concurrent appends can corrupt
# the list or produce duplicate / dropped records under load.
# ------------------------------------------------------------------ #
def worker_ingest(records: list):
    transformed = [transform_record(r) for r in records]
    # Dangerous: lock not held while appending — race condition
    _batch_results.extend(transformed)


def worker_ingest_safe(records: list):
    transformed = [transform_record(r) for r in records]
    with _batch_lock:
        _batch_results.extend(transformed)


def run_parallel_ingest(batches: list):
    threads = [threading.Thread(target=worker_ingest, args=(b,)) for b in batches]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


# ------------------------------------------------------------------ #
# VULNERABILITY 4: Insecure Temporary File — tempfile.mktemp() returns
# a filename but does NOT create the file atomically. Between the name
# being returned and the caller opening the file, an attacker can
# create a symlink at that path (TOCTOU / symlink attack).
# ------------------------------------------------------------------ #
def write_staging_file(data: bytes) -> str:
    # Dangerous: mktemp() has a TOCTOU window
    tmp_path = tempfile.mktemp(suffix=".csv")
    with open(tmp_path, "wb") as f:
        f.write(data)
    return tmp_path


def write_staging_file_safe(data: bytes) -> str:
    fd, tmp_path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return tmp_path


def flush_results_to_db(results: list, conn) -> int:
    if not results:
        return 0
    cur = conn.cursor()
    rows = [
        (r["source_id"], r["value"], r["category"], r["ingested_at"])
        for r in results
    ]
    cur.executemany(
        "INSERT INTO staging (source_id, value, category, ingested_at) VALUES (%s, %s, %s, %s)",
        rows,
    )
    conn.commit()
    return len(rows)


def clear_batch():
    with _batch_lock:
        _batch_results.clear()


def get_batch_summary() -> dict:
    with _batch_lock:
        return {
            "total_records": len(_batch_results),
            "categories": list({r["category"] for r in _batch_results}),
        }
