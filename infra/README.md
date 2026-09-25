# NeoRetail — Installation, configuration et validation de l'infrastructure

**Branche :** `feature/infra-setup`
**Environnement :** développement local avec Docker Compose, testé sous Windows et PowerShell.
**État :** PostgreSQL, MinIO, Kafka, Spark et Airflow ont été démarrés et testés. Le pipeline métier complet n'est pas encore implémenté.

Ce document retrace, dans l'ordre, la préparation de l'environnement, la configuration de chaque composant, les commandes d'installation, les vérifications réalisées et les incidents corrigés. Il décrit une infrastructure de développement local, et non une configuration destinée à la production.

> **État de publication :** les derniers changements Airflow et le DAG de test ont été validés localement. Leur présence sur la branche distante doit être confirmée après le prochain commit et le prochain push.

## Étape 1 — Préparer le poste de développement

L'infrastructure est conteneurisée pour éviter d'installer séparément PostgreSQL, Kafka, Spark et Airflow sur Windows. Docker Compose définit les services, leur réseau, leurs ports et leurs volumes persistants.

Installer **Git**, **Docker Desktop** avec Docker Compose et, pour l'édition des fichiers, **Visual Studio Code**. Sous Windows, Docker Desktop peut utiliser le moteur WSL 2. Démarrer Docker Desktop avant toute commande Docker. Prévoir suffisamment de mémoire : Spark, Kafka et les composants Airflow fonctionnent simultanément.

Dans PowerShell, contrôler les installations :

```powershell
git --version
docker --version
docker compose version
docker info
```

Si `docker info` échoue, vérifier d'abord que le moteur Docker est démarré. Les ports locaux `5432`, `9000`, `9001`, `9092`, `7077`, `8080`, `8081` et `8082` doivent être disponibles. En cas de conflit, adapter le port situé à gauche des correspondances de ports dans Compose, puis utiliser la nouvelle adresse locale.

## Étape 2 — Récupérer le dépôt et sélectionner la branche infrastructure

La branche d'infrastructure est **`feature/infra-setup`**. Elle contient la configuration des conteneurs et les scripts associés. Les commandes suivantes supposent que les changements décrits ici ont déjà été poussés sur cette branche.

Pour une première récupération :

```powershell
git clone https://github.com/wissal-bot/NeoRetail.git
cd NeoRetail
git fetch origin
git switch --track origin/feature/infra-setup
```

Si le dépôt est déjà présent et que la branche existe localement :

```powershell
git switch feature/infra-setup
git pull --ff-only origin feature/infra-setup
```

Vérifier la branche active et l'état du répertoire :

```powershell
git branch --show-current
git status -sb
```

Toutes les commandes des étapes suivantes doivent être exécutées **depuis la racine `NeoRetail/`**, sauf indication contraire.

## Étape 3 — Comprendre l'organisation des fichiers préparés

Le fichier `infra/docker-compose.yml` centralise la définition des services Docker. Le fichier `infra/.env.sample` sert de modèle pour la configuration locale. Le script `infra/scripts/init-kafka.sh` prépare automatiquement le topic Kafka. Le dossier `dags/` contient le pipeline de vérification Airflow.

```text
NeoRetail/
├── README.md
├── README_INFRA_ETAPES.md
├── .gitignore
├── infra/
│   ├── docker-compose.yml
│   ├── .env.sample
│   ├── .env                   # créé localement, exclu de Git
│   ├── airflow-passwords.json # créé localement, exclu de Git
│   └── scripts/
│       └── init-kafka.sh
├── dags/
│   └── test_neoretail.py
├── dbt/
├── quality/
├── ml/
├── bi/
└── docs/
```

Certains dossiers sont réservés aux prochaines phases et peuvent ne contenir qu'un fichier `.gitkeep`. Leur présence ne signifie pas que dbt, la qualité des données, le machine learning ou la BI sont déjà opérationnels. Le nom final du fichier de test doit être `test_neoretail.py` : un nom `test-neoretail.py` avait également été observé lors des essais locaux. Vérifier le nom réellement présent après récupération du dernier commit.

## Étape 4 — Créer la configuration locale et protéger les secrets

Les mots de passe ne sont pas enregistrés dans le dépôt. Copier le modèle fourni :

```powershell
Copy-Item infra/.env.sample infra/.env
```

Ouvrir `infra/.env` et renseigner les variables suivantes :

1. `POSTGRES_USER` : identifiant de la base PostgreSQL. La configuration testée utilise `neoretail`.
2. `POSTGRES_PASSWORD` : mot de passe local de PostgreSQL, à générer.
3. `POSTGRES_DB` : nom de la base utilisée par Airflow. La valeur testée est `airflow`.
4. `MINIO_ROOT_USER` et `MINIO_ROOT_PASSWORD` : identifiants d'administration de MinIO, à définir localement.
5. `AIRFLOW_UID` : identifiant Unix utilisé par les conteneurs Airflow. La valeur testée sous Windows est `50000`.
6. `AIRFLOW_FERNET_KEY` : clé de chiffrement Airflow, à générer au format Fernet.
7. `AIRFLOW_JWT_SECRET` : secret aléatoire de signature des jetons Airflow, à générer.
8. `AIRFLOW_ADMIN_PASSWORD` : mot de passe local servant à préparer le fichier JSON d'authentification Airflow. Cette variable n'est pas directement lue par Airflow.

Pour générer une clé Fernet valide :

```powershell
docker run --rm apache/airflow:3.1.0 python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Reporter la valeur obtenue **uniquement dans le fichier local**. Pour générer une chaîne aléatoire destinée au secret JWT ou au mot de passe administrateur, exécuter séparément :

```powershell
$bytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
[Convert]::ToBase64String($bytes)
```

Le mot de passe PostgreSQL est inséré dans une URL de connexion SQLAlchemy. Certains caractères spéciaux nécessitent un encodage URL ; pour une installation locale simple, utiliser un mot de passe alphanumérique suffisamment long, ou encoder correctement sa valeur.

**Contrôle de sécurité :** les fichiers `infra/.env` et `infra/airflow-passwords.json` doivent rester locaux. Ne jamais copier leurs valeurs dans la documentation, les captures d'écran, les journaux partagés ou les commits. Renouveler toute clé déjà divulguée.

## Étape 5 — Préparer l'authentification locale d'Airflow

La configuration utilise **Apache Airflow 3.1.0** avec le *Simple Auth Manager* pour les essais locaux. Un fichier JSON distinct fournit le mot de passe de l'utilisateur `admin`.

Après avoir renseigné `AIRFLOW_ADMIN_PASSWORD` dans `infra/.env`, créer `infra/airflow-passwords.json` depuis la racine du projet :

```powershell
$password = (Get-Content infra/.env | Where-Object {
    $_ -match '^AIRFLOW_ADMIN_PASSWORD='
}) -replace '^AIRFLOW_ADMIN_PASSWORD=', ''

if (-not $password) { throw 'AIRFLOW_ADMIN_PASSWORD est absent de infra/.env' }

@{ admin = $password } |
    ConvertTo-Json -Compress |
    Set-Content -Path infra/airflow-passwords.json -Encoding ascii

Remove-Variable password
```

Le fichier JSON est monté dans les conteneurs Airflow sous `/opt/airflow/airflow-passwords.json`. **Le montage doit être en lecture-écriture** : le montage initial en lecture seule (`:ro`) a provoqué une erreur `Read-only file system` et des redémarrages. Cette erreur a été corrigée en retirant `:ro` du montage.

Vérifier que Git ignore les deux fichiers confidentiels :

```powershell
git check-ignore infra/.env infra/airflow-passwords.json
```

Les deux chemins doivent apparaître. Vérifier également que `.env.sample` contient seulement des exemples ou des emplacements réservés, jamais de véritables secrets.

## Étape 6 — Vérifier Docker Compose avant le démarrage

Le fichier `infra/docker-compose.yml` configure un réseau Docker commun, les volumes de données et les dépendances entre services. Les conteneurs communiquent entre eux par leur **nom de service**. Par exemple, Airflow contacte PostgreSQL avec `postgres:5432`, et non `localhost:5432`.

Valider la syntaxe du fichier et l'interpolation des variables :

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml config --quiet
```

L'absence de message indique que la validation de la configuration s'est terminée sans erreur. Cette commande ne prouve pas encore que les services démarreront : les vérifications fonctionnelles viennent ensuite.

## Étape 7 — Démarrer et tester PostgreSQL

PostgreSQL fournit la base de métadonnées d'Airflow. L'image utilisée est `postgres:17`, avec le service `postgres`, le conteneur `neoretail-postgres`, le port local `5432` et le volume persistant `postgres_data`.

Démarrer PostgreSQL :

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d postgres
```

Vérifier son état :

```powershell
docker ps --filter "name=neoretail-postgres"
```

**Test réalisé :** PostgreSQL a atteint l'état `Healthy`, permettant ensuite l'initialisation de la base Airflow. Le contrôle de santé actuel utilise `pg_isready -U neoretail -d airflow`. Si `POSTGRES_USER` ou `POSTGRES_DB` change, modifier également ce contrôle dans Compose.

**Point important :** les variables d'initialisation de PostgreSQL ne réinitialisent pas une base déjà créée dans le volume `postgres_data`. Un changement ultérieur d'identifiants doit tenir compte des données existantes.

## Étape 8 — Démarrer MinIO et préparer les zones du Data Lakehouse

MinIO fournit le stockage objet compatible S3. Il est configuré avec le service `minio`, le conteneur `neoretail-minio` et le volume persistant `minio_data`. L'image actuelle est une image communautaire `ghcr.io/golithus/minio` verrouillée par empreinte (*digest*) dans Compose. Sa provenance doit être réévaluée avant un usage sensible ou un déploiement en production.

Démarrer MinIO :

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d minio
```

Ouvrir la console sur `http://localhost:9001` et se connecter avec les identifiants définis dans `infra/.env`. L'API S3 est exposée sur `http://localhost:9000`. Depuis un autre conteneur, l'adresse de l'API est `http://minio:9000`.

Créer **manuellement** trois buckets dans la console :

1. `bronze` : zone prévue pour les données brutes ingérées.
2. `silver` : zone prévue pour les données nettoyées et transformées.
3. `gold` : zone prévue pour les données consolidées et exploitables.

**Tests réalisés :** l'interface MinIO a été ouverte, l'API a répondu au contrôle HTTP et les trois buckets ont été créés. La création automatique de ces buckets n'est **pas encore implémentée** ; elle doit être reproduite après une installation neuve.

## Étape 9 — Configurer Kafka et automatiser la création du topic

Apache Kafka `3.9.1` est configuré en mode **KRaft**, avec un seul conteneur assurant les fonctions de broker et de contrôleur. Ce choix convient aux tests locaux, mais n'apporte pas de haute disponibilité.

Le port `localhost:9092` est prévu pour les clients exécutés sur Windows. Les conteneurs utilisent `kafka:29092`. Le port interne `9093` est réservé au contrôleur. Le volume `kafka_data` conserve les données Kafka.

Démarrer le broker :

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d kafka
```

Le script `infra/scripts/init-kafka.sh` a été préparé pour attendre la disponibilité de Kafka puis créer, si nécessaire, le topic **`clickstream`** avec **3 partitions** et un **facteur de réplication de 1**. Exécuter le conteneur d'initialisation :

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up kafka-init
```

Contrôler la configuration du topic :

```powershell
docker exec neoretail-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic clickstream
```

**Tests réalisés :** le broker a démarré, le topic `clickstream` a été créé, un message JSON a été envoyé puis consommé, et le script d'initialisation a été testé à nouveau alors que le topic existait déjà. Cette seconde exécution a confirmé le comportement attendu sans recréation inutile.

Le conteneur `kafka-init` doit normalement s'arrêter une fois son travail terminé. Son état `Exited (0)` n'est donc pas une panne.

## Étape 10 — Déployer Spark Master et Spark Worker

Apache Spark `3.5.6` est déployé avec deux services : `spark-master` et `spark-worker`. Le Master accepte les connexions sur `spark://spark-master:7077` et expose son interface sur `http://localhost:8080`. L'interface du Worker est accessible sur `http://localhost:8081`.

Le Worker a été configuré avec **2 cœurs** et **1 Gio de mémoire**. Démarrer les deux services :

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d spark-master spark-worker
```

Ouvrir l'interface du Master et vérifier que le Worker y apparaît. Consulter ensuite l'interface du Worker pour confirmer son état.

**Test réalisé :** le job d'exemple **SparkPi** s'est exécuté avec succès. Ce résultat valide le fonctionnement du cluster Spark local. Il ne valide pas encore une chaîne complète Kafka → Spark → MinIO : cette intégration reste à développer.

## Étape 11 — Configurer les composants Airflow

Apache Airflow `3.1.0` orchestre les futurs pipelines. Son architecture locale comprend quatre services :

1. `airflow-init` prépare la base de métadonnées avec `airflow db migrate`, puis s'arrête normalement.
2. `airflow-apiserver` fournit l'API et l'interface web, exposées sur `http://localhost:8082`.
3. `airflow-scheduler` planifie les tâches et les lance avec `LocalExecutor`.
4. `airflow-dag-processor` charge et analyse les fichiers Python du dossier `dags/`.

Le bloc partagé `x-airflow-common` dans Compose centralise l'image, les variables et les volumes. Les réglages essentiels sont les suivants :

```yaml
AIRFLOW__CORE__EXECUTOR: LocalExecutor
AIRFLOW__CORE__EXECUTION_API_SERVER_URL: http://airflow-apiserver:8080/execution/
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY}
AIRFLOW__API_AUTH__JWT_SECRET: ${AIRFLOW_JWT_SECRET}
AIRFLOW__CORE__LOAD_EXAMPLES: "false"
AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_USERS: "admin:admin"
AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_PASSWORDS_FILE: /opt/airflow/airflow-passwords.json
```

Les montages partagés sont :

```yaml
- ../dags:/opt/airflow/dags
- airflow_logs:/opt/airflow/logs
- ./airflow-passwords.json:/opt/airflow/airflow-passwords.json
```

Le dossier `dags/` reste modifiable sur le poste de développement ; ses fichiers sont directement visibles dans les conteneurs. Les journaux Airflow sont conservés dans le volume `airflow_logs`.

Initialiser la base, puis démarrer les trois services persistants :

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up airflow-init

docker compose --env-file infra/.env -f infra/docker-compose.yml up -d airflow-apiserver airflow-scheduler airflow-dag-processor
```

Vérifier leur état :

```powershell
docker ps --filter "name=neoretail-airflow"
```

Ouvrir `http://localhost:8082`, puis se connecter avec l'utilisateur `admin` et le mot de passe configuré localement.

**Tests réalisés :** l'API Server, le Scheduler et le DAG Processor ont démarré ; l'interface a été ouverte et la connexion administrateur a fonctionné. Le test d'exécution du DAG a ensuite permis de vérifier la communication interne, au-delà du simple état `Up` des conteneurs.

## Étape 12 — Créer et exécuter le premier DAG de vérification

Le fichier `dags/test_neoretail.py` contient un DAG nommé `test_neoretail`. Il ne se déclenche pas automatiquement (`schedule=None`) : son exécution est volontairement manuelle pour contrôler l'infrastructure.

Le contenu validé localement est :

```python
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
```

Dans l'interface Airflow, rechercher `test_neoretail`, déclencher une nouvelle exécution et ouvrir la tâche `verifier_pipeline`. Une exécution réussie doit afficher l'état **Success** et le message suivant dans les journaux :

```text
NeoRetail : le pipeline Airflow fonctionne !
```

**Résultat obtenu :** après correction de la configuration réseau d'Airflow, une nouvelle exécution du DAG s'est terminée avec succès. Ce test confirme qu'Airflow peut charger le fichier, planifier la tâche et l'exécuter.

## Étape 13 — Comprendre les incidents rencontrés et leurs corrections

### 13.1 — Redémarrage d'Airflow à cause du fichier de mots de passe

Le fichier `airflow-passwords.json` avait d'abord été monté en lecture seule. Le Simple Auth Manager a tenté d'y accéder en écriture et a déclenché une erreur `OSError: [Errno 30] Read-only file system`.

**Correction appliquée :** retirer `:ro` du montage de ce fichier, puis recréer les services concernés. Le fichier reste exclu de Git malgré ce montage en lecture-écriture.

### 13.2 — Connexion à l'interface Airflow

L'authentification initiale nécessitait de définir explicitement le fichier local de mots de passe. Le JSON contenant le compte `admin` a été créé, puis son chemin a été déclaré dans `AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_PASSWORDS_FILE`.

**Résultat :** la connexion à l'interface sur le port `8082` a été validée.

### 13.3 — DAG absent ou nom de fichier incohérent

Pendant les vérifications, le nom `test-neoretail.py` a été observé dans le dossier monté, alors que le nom attendu pour la version finale est `test_neoretail.py`. En cas d'absence du DAG, vérifier le fichier réellement monté et les erreurs d'import :

```powershell
docker exec neoretail-airflow-dag-processor ls -l /opt/airflow/dags
docker exec neoretail-airflow-dag-processor airflow dags list-import-errors
docker logs --tail 100 neoretail-airflow-dag-processor
```

Vérifier le nom exact du fichier dans le dépôt après le prochain commit et laisser au DAG Processor le temps de l'analyser.

### 13.4 — Échec d'exécution avec `Connection refused`

La première exécution de `test_neoretail` s'est terminée en échec. Le Scheduler signalait un décalage entre l'état `queued` de la tâche et l'état `failed` rapporté par `LocalExecutor`. Ses journaux montraient surtout l'erreur :

```text
httpx.ConnectError: [Errno 111] Connection refused
```

**Cause identifiée :** le processus d'exécution n'arrivait pas à joindre l'API d'exécution d'Airflow. Les conteneurs doivent communiquer par le nom du service Docker, et non par `localhost`.

**Correction appliquée :** ajouter cette variable dans l'environnement partagé `x-airflow-common` :

```yaml
AIRFLOW__CORE__EXECUTION_API_SERVER_URL: http://airflow-apiserver:8080/execution/
```

Recréer les services pour appliquer le changement :

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d --force-recreate airflow-apiserver airflow-scheduler airflow-dag-processor
```

Les trois services sont ensuite apparus à l'état `Up`, puis une **nouvelle** exécution du DAG a réussi. L'ancienne exécution échouée reste visible dans l'historique ; elle ne doit pas être confondue avec le nouveau test.

## Étape 14 — Effectuer la vérification générale de l'infrastructure

Après installation, vérifier les services dans cet ordre :

1. **PostgreSQL :** le conteneur `neoretail-postgres` est à l'état `Healthy`.
2. **MinIO :** la console sur `http://localhost:9001` est accessible et les buckets `bronze`, `silver` et `gold` sont présents.
3. **Kafka :** le broker fonctionne ; la commande de description du topic confirme `clickstream` et ses trois partitions.
4. **Spark :** l'interface du Master sur `http://localhost:8080` affiche le Worker ; un job simple peut être exécuté.
5. **Airflow :** l'interface sur `http://localhost:8082` est accessible ; `test_neoretail` est visible et une nouvelle exécution se termine en `Success`.

Afficher l'ensemble des conteneurs, y compris ceux qui s'arrêtent après initialisation :

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml ps -a
```

Les services `airflow-init` et `kafka-init` peuvent être arrêtés normalement avec un code de sortie `0`. Pour diagnostiquer une anomalie, consulter les journaux du service concerné sans diffuser de secrets :

```powershell
docker logs --tail 100 neoretail-airflow-scheduler
docker logs --tail 100 neoretail-airflow-apiserver
docker logs --tail 100 neoretail-airflow-dag-processor
```

Un conteneur marqué `Up` n'est pas, à lui seul, la preuve que son application fonctionne. Les vérifications de connexion, de traitement et d'exécution restent nécessaires.

## Étape 15 — Arrêter, redémarrer et conserver les données

Pour arrêter les services sans supprimer les données persistantes :

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml down
```

Pour les redémarrer :

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

Pour appliquer une modification de la configuration Airflow, recréer uniquement les services concernés avec la commande de l'étape 13.4.

**Ne pas utiliser `docker compose down -v` pour un simple arrêt.** L'option `-v` supprime les volumes gérés par Compose, notamment ceux de PostgreSQL, MinIO, Kafka et des journaux Airflow. Les données des volumes Docker ne sont pas stockées dans Git et ne sont pas récupérées avec un `git clone`.

## Étape 16 — Vérifier les fichiers avant le commit

La branche `feature/infra-setup` doit contenir la configuration Compose, le modèle `.env.sample`, le script d'initialisation Kafka, le DAG de test et cette documentation. Les fichiers locaux de secrets doivent rester absents de l'index Git.

Contrôler l'état du dépôt et les exclusions :

```powershell
git branch --show-current
git status -sb
git check-ignore infra/.env infra/airflow-passwords.json
git diff -- infra/docker-compose.yml infra/.env.sample
```

Avant tout commit, vérifier que `infra/docker-compose.yml` contient bien l'adresse `http://airflow-apiserver:8080/execution/` et que le montage du fichier JSON ne comporte plus `:ro`. Vérifier également le nom final du DAG, le contenu du modèle `.env.sample` et l'absence de secrets dans les fichiers suivis.

Ajouter explicitement les fichiers souhaités avec `git add <chemin>`, puis examiner `git diff --cached` avant de créer le commit. Les dernières corrections Airflow et la documentation doivent être poussées avant qu'une nouvelle installation puisse être reproduite à partir de la branche distante.

## Étape 17 — Identifier les éléments encore à développer

L'infrastructure de base est opérationnelle sur le poste où les tests ont été effectués. Sa reproduction complète sur un autre poste reste à vérifier après publication des derniers changements.

Les étapes suivantes ne sont **pas encore déclarées terminées** dans ce périmètre : automatisation de la création des buckets MinIO ; ingestion de données métier ; pipeline Kafka → Spark → MinIO ; traitement réel des zones Bronze, Silver et Gold ; mise en place de tables Delta ou Iceberg ; modèles dbt ; contrôles de qualité ; MLflow ; visualisation BI ; supervision ; intégration continue ; déploiement distant ; et renforcement de la sécurité pour la production.

La priorité immédiate est de publier les fichiers effectivement validés, puis de refaire l'installation et les tests décrits dans ce document à partir de la version distante de `feature/infra-setup`.
