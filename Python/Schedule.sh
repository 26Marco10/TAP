#!/bin/bash

# Ottieni il percorso della cartella corrente
SCRIPT_DIR=$(dirname "$0")

while true; do
    # Esegui i due script Python nella stessa cartella dello script Bash
    python3 "$SCRIPT_DIR/Global.py"
    python3 "$SCRIPT_DIR/Italy.py"

    sleep 86400
done
