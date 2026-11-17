#!/usr/bin/env bash
# Goryachaya kopiya bazy (bezopasno dazhe pri rabotayushchem servere).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p data/backups
STAMP=$(date +%Y%m%d_%H%M%S)
sqlite3 data/database.db ".backup 'data/backups/db_${STAMP}.db'"
find data/backups -name 'db_*.db' -mtime +14 -delete
echo "  bekap: data/backups/db_${STAMP}.db"
