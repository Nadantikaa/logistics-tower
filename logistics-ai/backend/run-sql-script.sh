#!/bin/bash
# Access MySQL CLI from the running container

docker-compose exec db mysql -u logistics_user -p logistics_db -e "source /docker-entrypoint-initdb.d/01-init.sql"
