#!/bin/sh
# Relance le collecteur jusqu'a ce qu'il annonce la grille complete.
# Detache : survit a la fermeture du terminal et aux delais de la session.
cd "$(dirname "$0")/../.." || exit 1
LOG=data/calibration_grid/collect.log
while true; do
    ./venv/bin/python -u scripts/calibration_grid/collect.py --backoff 90 >> "$LOG" 2>&1
    if [ $? -eq 0 ]; then
        echo "$(date '+%F %T')  grille complete" >> "$LOG"
        break
    fi
    echo "$(date '+%F %T')  reprise dans 60 s" >> "$LOG"
    sleep 60
done
