FROM python:3.12-slim

# Install system dependencies including postgresql-client
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Set working directory
WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Configure poetry
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --only=main

# Copy application code
COPY . .

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "Starting DevCycle Application..."\n\
\n\
# Wait for database to be ready\n\
echo "Waiting for database to be ready..."\n\
while ! pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USERNAME; do\n\
  echo "Database is unavailable - sleeping"\n\
  sleep 1\n\
done\n\
echo "Database is ready!"\n\
\n\
# Run migrations\n\
echo "Running database migrations..."\n\
poetry run aerich upgrade\n\
\n\
# Start the application\n\
echo "Starting FastAPI application..."\n\
exec poetry run uvicorn devcycle.api.app:app --host 0.0.0.0 --port 8000 --reload' > /app/start.sh

# Make startup script executable
RUN chmod +x /app/start.sh

# Use startup script
CMD ["/app/start.sh"]
