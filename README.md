## V6 — Production Deployment and Security

NexusAI is a multi-agent orchestration platform built with LangGraph, FastAPI, Ollama, ChromaDB, and SQLite. V6 adds deployment and operational safeguards on top of the existing orchestration, retrieval, verification, and observability capabilities.

### V6 capabilities

- Containerized deployment using Docker and Docker Compose
- API-key authentication for application endpoints
- Basic per-client rate limiting
- Persistent Docker volumes for application data and evaluation results
- Automated tests through GitHub Actions
- Health checks and Prometheus-compatible metrics
- Environment-based configuration for deployment

### Architecture

1. FastAPI accepts and validates client requests.
2. Security middleware checks API keys and applies rate limits.
3. LangGraph orchestrates specialist agents and workflow routing.
4. ChromaDB provides document retrieval, while analytics tools handle supported data queries.
5. The critic and approval workflow provides verification and controlled human intervention.
6. Observability captures request metrics, workflow events, and execution traces.

### Run locally with Docker

1. Install Docker Desktop and start Ollama.
2. Download the configured Ollama model.
3. Copy `.env.example` to `.env` and set a strong `NEXUSAI_API_KEY`.
4. Build and start the service:

   ```powershell
   docker compose up --build -d
   ```

5. Open `http://127.0.0.1:8000/docs`.
6. Select **Authorize**, enter the API key, and test a protected endpoint.

### Security and operational limitations

The included rate limiter uses in-memory storage and is intended for a single application process. Multi-worker and multi-replica deployments need a shared rate-limit store. Keep the service behind HTTPS and a trusted reverse proxy when exposed outside localhost. Protect metrics and administrative endpoints according to your deployment requirements. Never commit secrets, uploaded sensitive documents, or runtime databases to source control.

### Testing

Run `python -m pytest -v` before building the container. GitHub Actions runs syntax checks and the test suite on pushes and pull requests. Evaluation quality scores are automated proxies and should be supplemented with reviewed test cases and human assessment.
