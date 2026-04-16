#!/bin/bash
# Reset the database by removing volumes and recreating the container
# WARNING: This will delete all data in the database!

echo "⚠️  WARNING: This will DELETE all database data!"
read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Operation cancelled."
    exit 0
fi

echo "Stopping services..."
docker-compose down

echo "Removing database volume..."
docker volume rm logistics-ai_db_data 2>/dev/null || true

echo "Rebuilding and starting services..."
docker-compose up --build -d

echo "Waiting for database to be ready..."
sleep 5

echo "Database has been reset! Services are running."
docker-compose ps
