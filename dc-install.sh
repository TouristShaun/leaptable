wget -O docker-compose.yaml  https://git.leaptable.co/docker-compose.yaml
wget -O .env.local https://git.leaptable.co/.env.local
wget -O 01-init.sh https://git.leaptable.co/01-init.sh
wget -O 02-init-workspace https://git.leaptable.co/02-init-workspace.sh
wget -O init-meta-db.sql https://git.leaptable.co/init-meta-db.sql

# Populate .env.local with values accordingly.
# .env.local

mkdir -p ~/.leaptable/postgresql