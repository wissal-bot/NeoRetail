from __future__ import annotations

import hashlib
import os
from datetime import datetime

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import s3fs

from airflow.sdk import dag, task

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "neoretail")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "change_me")
BUCKET = "neoretail"
RAW_PATH = "/opt/airflow/raw"


def _s3() -> s3fs.S3FileSystem:
    return s3fs.S3FileSystem(
        key=MINIO_ACCESS_KEY,
        secret=MINIO_SECRET_KEY,
        endpoint_url=MINIO_ENDPOINT,
        use_ssl=False,
    )


def _sha256(val: str) -> str:
    if pd.isna(val) or val == "":
        return val
    return hashlib.sha256(str(val).encode()).hexdigest()


def _write_parquet(df: pd.DataFrame, s3: s3fs.S3FileSystem, table: str, ds: str) -> None:
    path = f"{BUCKET}/bronze/{table}/dt={ds}/data.parquet"
    arrow_table = pa.Table.from_pandas(df, preserve_index=False)
    with s3.open(path, "wb") as f:
        pq.write_table(arrow_table, f)


def _delete_partition(s3: s3fs.S3FileSystem, table: str, ds: str) -> None:
    partition = f"{BUCKET}/bronze/{table}/dt={ds}"
    if s3.exists(partition):
        s3.rm(partition, recursive=True)


@dag(
    dag_id="dag_referentiels_s1",
    description="S1 — Ingestion batch des référentiels vers Bronze (MinIO)",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["neoretail", "s1", "batch", "referentiels"],
)
def dag_referentiels():

    @task
    def ingest_customers(ds: str = None) -> None:
        df = pd.read_csv(f"{RAW_PATH}/customers/customers.csv.gz", compression="gzip")
        df["email_pseudo"] = df["email_pseudo"].apply(_sha256)
        df["phone_pseudo"] = df["phone_pseudo"].apply(_sha256)
        s3 = _s3()
        _delete_partition(s3, "customers", ds)
        _write_parquet(df, s3, "customers", ds)

    @task
    def ingest_products(ds: str = None) -> None:
        df = pd.read_csv(f"{RAW_PATH}/products/products.csv.gz", compression="gzip")
        s3 = _s3()
        _delete_partition(s3, "products", ds)
        _write_parquet(df, s3, "products", ds)

    @task
    def ingest_stores(ds: str = None) -> None:
        df = pd.read_csv(f"{RAW_PATH}/stores/stores.csv.gz", compression="gzip")
        s3 = _s3()
        _delete_partition(s3, "stores", ds)
        _write_parquet(df, s3, "stores", ds)

    ingest_customers()
    ingest_products()
    ingest_stores()


dag_referentiels()
