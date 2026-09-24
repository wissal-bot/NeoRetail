#!/bin/bash

set -e

BOOTSTRAP_SERVER="${BOOTSTRAP_SERVER:-localhost:9092}"
TOPIC="clickstream"

echo "Initialisation de Kafka..."

# Attendre que Kafka accepte les connexions.
until /opt/kafka/bin/kafka-broker-api-versions.sh \
    --bootstrap-server "$BOOTSTRAP_SERVER" > /dev/null 2>&1
do
    echo "Kafka n'est pas encore disponible. Nouvelle tentative dans 5 secondes..."
    sleep 5
done

echo "Kafka est disponible."

# Vérifier si le topic existe.
if /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server "$BOOTSTRAP_SERVER" \
    --describe \
    --topic "$TOPIC" > /dev/null 2>&1
then
    echo "Le topic $TOPIC existe déjà."
else
    echo "Création du topic $TOPIC..."

    /opt/kafka/bin/kafka-topics.sh \
        --bootstrap-server "$BOOTSTRAP_SERVER" \
        --create \
        --topic "$TOPIC" \
        --partitions 3 \
        --replication-factor 1

    echo "Topic créé avec succès."
fi

echo "Initialisation terminée."