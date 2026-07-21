FROM python:3.14-rc-slim

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy the dependency files first
COPY pyproject.toml ./

# Install dependencies using uv directly to system Python
RUN uv pip install --system -e .

# Copy the rest of the application
COPY . .

# Expose the Cloud Run port
EXPOSE 8080

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
