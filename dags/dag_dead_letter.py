from __future__ import annotations

import json
import os
from datetime import datetime

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import s3fs
from kafka import KafkaAdminClient, KafkaConsumer
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError

from airflow.sdk import dag, task

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
DEAD_LETTER_TOPIC = "clickstream-dead-letter"
CONSUMER_GROUP = "dead-letter-monitor"

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "neoretail")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "change_me")
BUCKET = "neoretail"

POLL_TIMEOUT_MS = 5_000


def _s3() -> s3fs.S3FileSystem:
    return s3fs.S3FileSystem(
        key=MINIO_ACCESS_KEY,
        secret=MINIO_SECRET_KEY,
        endpoint_url=MINIO_ENDPOINT,
        use_ssl=False,
    )


def _ensure_topic() -> None:
    admin = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP)
    try:
        admin.create_topics([NewTopic(DEAD_LETTER_TOPIC, num_partitions=3, replication_factor=1)])
    except TopicAlreadyExistsError:
        pass
    finally:
        admin.close()


def _write_parquet(records: list[dict], s3: s3fs.S3FileSystem, ds: str) -> None:
    df = pd.DataFrame(records)
    path = f"{BUCKET}/bronze/dead_letter/dt={ds}/data.parquet"
    table = pa.Table.from_pandas(df, preserve_index=False)
    with s3.open(path, "wb") as f:
        pq.write_table(table, f)


@dag(
    dag_id="dag_dead_letter_s2",
    description="S2 — Monitoring du topic dead-letter clickstream vers Bronze",
    start_date=datetime(2026, 1, 1),
    schedule="@hourly",
    catchup=False,
    tags=["neoretail", "s2", "streaming", "dead-letter"],
)
def dag_dead_letter():

    @task
    def ensure_topic() -> None:
        _ensure_topic()

    @task
    def consume_and_store(ds: str = None) -> int:
        consumer = KafkaConsumer(
            DEAD_LETTER_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP,
            group_id=CONSUMER_GROUP,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            consumer_timeout_ms=POLL_TIMEOUT_MS,
        )

        records = []
        for msg in consumer:
            record = msg.value if isinstance(msg.value, dict) else {"raw": str(msg.value)}
            record["_partition"] = msg.partition
            record["_offset"] = msg.offset
            record["_consumed_at"] = ds
            records.append(record)

        consumer.close()

        if not records:
            return 0

        s3 = _s3()
        partition_path = f"{BUCKET}/bronze/dead_letter/dt={ds}"
        if s3.exists(partition_path):
            s3.rm(partition_path, recursive=True)

        _write_parquet(records, s3, ds)
        return len(records)

    ensure_topic() >> consume_and_store()


dag_dead_letter()
