wget -O docker-compose.yaml  https://git.leaptable.co/docker-compose.yaml \
    -O .env.local https://git.leaptable.co/.env.local \
    -O 01-init.sh https://git.leaptable.co/01-init.sh \
    -O init-meta-db.sql https://git.leaptable.co/init-meta-db.sql

# Populate .env.local with values accordingly.
# .env.local

mkdir -p ~/.leaptable/postgresql