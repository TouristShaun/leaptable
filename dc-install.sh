wget -O docker-compose.yaml  https://git.reframe.is/docker-compose.yaml
wget -O .env.local https://git.reframe.is/.env.local
wget -O 01-init.sh https://git.reframe.is/01-init.sh
wget -O 02-init-workspace https://git.reframe.is/02-init-workspace.sh
wget -O init-meta-db.sql https://git.reframe.is/init-meta-db.sql

mkdir -p ~/.reframe/postgresql