from datetime import datetime

from airflow.sdk import dag, task


@dag(
    dag_id="test_neoretail",
    description="Premier pipeline de test NeoRetail",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["neoretail", "test"],
)
def test_neoretail():

    @task
    def verifier_pipeline():
        print("NeoRetail : le pipeline Airflow fonctionne !")
        return "SUCCESS"

    verifier_pipeline()


test_neoretail()