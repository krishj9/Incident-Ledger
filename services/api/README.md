# Incident Ledger API

FastAPI backend service for Incident Ledger.

## Overview

The Incident Ledger API is the backend service that powers the Incident Ledger application. It enables child-care staff to document significant incidents promptly, allows directors to review and approve them, and provides primary guardians with access to approved child-specific incident reports.

**Note:** This is a controlled synthetic-data demonstration, not a real-center deployment.

## Features

- **Incident Management**: Document, track, and manage child-care incidents
- **Approval Workflow**: Multi-level review and approval process for incident reports
- **Guardian Access**: Secure access for primary guardians to view approved incident reports
- **Authentication**: Microsoft Entra ID (OIDC) integration for secure user authentication
- **Database**: PostgreSQL with async support for high-performance operations
- **Logging**: Configurable logging levels for debugging and monitoring

## Tech Stack

- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with asyncpg driver
- **Authentication**: OIDC (Microsoft Entra ID)
- **AI Integration**: Google Vertex AI / Gemini for enhanced functionality
- **Deployment**: Ready for containerization and cloud deployment

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL 13+
- Docker (optional, for containerized development)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/krishj9/Incident-Ledger.git
   cd Incident-Ledger/services/api
   ```

2. **Create environment configuration**
   ```bash
   cp .env.example .env
   ```

3. **Configure `.env` file**
   - Update database credentials
   - Set OIDC provider details (or use `INCIDENT_LEDGER_MOCK_AUTH=true` for local testing)
   - Configure CORS origins for your frontend
   - Add Google Cloud project ID and Gemini model details

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run database migrations** (if applicable)
   ```bash
   # Add migration commands here
   ```

6. **Start the API server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

The API will be available at `http://localhost:8000`

## Configuration

### Environment Variables

Key environment variables (see `.env.example` for full list):

- **`INCIDENT_LEDGER_DATABASE_URL`**: PostgreSQL connection string
- **`INCIDENT_LEDGER_OIDC_ISSUER`**: Microsoft Entra ID token issuer URL
- **`INCIDENT_LEDGER_OIDC_AUDIENCE`**: Application client ID
- **`INCIDENT_LEDGER_MOCK_AUTH`**: Set to `true` to bypass OIDC validation (local dev only)
- **`INCIDENT_LEDGER_CORS_ORIGINS`**: Comma-separated list of allowed frontend origins
- **`INCIDENT_LEDGER_LOG_LEVEL`**: Logging level (DEBUG, INFO, WARNING, ERROR)
- **`INCIDENT_LEDGER_GCP_PROJECT_ID`**: Google Cloud project ID for Vertex AI
- **`INCIDENT_LEDGER_GEMINI_MODEL`**: Gemini model version to use

### Demo Mode

For testing without real authentication:
```env
INCIDENT_LEDGER_DEMO_ONLY=true
INCIDENT_LEDGER_ALLOWED_CENTER_CODES=["DEMO-MGLC-01"]
INCIDENT_LEDGER_MOCK_AUTH=true
```

## API Endpoints

Endpoints will be documented here. Access the interactive API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Authentication

The API uses OpenID Connect (OIDC) via Microsoft Entra ID for authentication. In production, all requests must include a valid JWT token in the `Authorization` header.

For local development, set `INCIDENT_LEDGER_MOCK_AUTH=true` to bypass token validation.

## Database

PostgreSQL is required for the application. Connection details are configured via `INCIDENT_LEDGER_DATABASE_URL`.

Example local setup:
```bash
docker run --name incident-ledger-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=incident_ledger \
  -p 5432:5432 \
  postgres:15
```

## Logging

Configure logging level with `INCIDENT_LEDGER_LOG_LEVEL`. Available levels: DEBUG, INFO, WARNING, ERROR, CRITICAL.

## AI Integration

The API integrates with Google Vertex AI and Gemini for enhanced incident analysis and categorization. Configure:
- `INCIDENT_LEDGER_GCP_PROJECT_ID`: Your Google Cloud project ID
- `INCIDENT_LEDGER_GEMINI_MODEL`: Model identifier (e.g., `gemini-2.5-flash`)

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black .

# Lint
pylint .

# Type checking
mypy .
```

## Deployment

### Docker

```bash
docker build -t incident-ledger-api .
docker run -p 8000:8000 --env-file .env incident-ledger-api
```

### Production Checklist

- [ ] Set `INCIDENT_LEDGER_MOCK_AUTH=false`
- [ ] Configure real OIDC credentials
- [ ] Set appropriate `INCIDENT_LEDGER_LOG_LEVEL`
- [ ] Use environment-specific configuration
- [ ] Enable HTTPS for all endpoints
- [ ] Set up database backups
- [ ] Configure monitoring and alerting

## Related Services

- **Frontend**: TypeScript/React application in `services/web`
- **Main Repository**: See root `README.md` for full project overview

## Support

For issues, questions, or contributions, please refer to the main repository's contribution guidelines.

## License

See LICENSE file in the root of the repository.
