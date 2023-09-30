wget -O docker-compose.yaml  https://git.reframe.co/docker-compose.yaml
wget -O .env.local https://git.reframe.co/.env.local
wget -O 01-init.sh https://git.reframe.co/01-init.sh
wget -O 02-init-workspace https://git.reframe.co/02-init-workspace.sh
wget -O init-meta-db.sql https://git.reframe.co/init-meta-db.sql

mkdir -p ~/.reframe/postgresql