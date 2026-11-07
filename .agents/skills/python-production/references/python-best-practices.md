Python Best Practices for Production-Ready Applications

A practical guide to building maintainable, secure, testable, and production-ready Python applications, including AI-agent projects.

Table of Contents
Recommended Python Stack
Dependency Management with uv
Project Structure
Code Quality and Formatting
Testing Strategy
Configuration and Secrets
Logging and Observability
Security Best Practices
Database Best Practices
Docker and CI/CD
AI-Agent Production Practices
Daily Development Workflow
Production Readiness Checklist
Useful Documentation
1. Recommended Python Stack
Concern	Recommended Tool	Purpose
Package management	uv	Dependencies, virtual environments, lockfiles
Web framework	FastAPI	Building HTTP APIs
Data validation	Pydantic	Validating inputs and outputs
Configuration	pydantic-settings	Managing application settings
Linting	Ruff	Detecting common code issues
Formatting	Ruff	Consistent code style
Type checking	mypy or Pyright	Detecting type errors
Testing	pytest	Unit and integration tests
Coverage	pytest-cov	Measuring test coverage
Git hooks	pre-commit	Running checks before commits
Security scanning	Bandit	Detecting common Python security issues
Dependency auditing	pip-audit	Checking known dependency vulnerabilities
Database migrations	Alembic	Version-controlling schema changes
Database	PostgreSQL	Persistent relational storage
Logging	Python logging or structlog	Structured application logs
Observability	OpenTelemetry	Distributed traces and instrumentation
Containerization	Docker	Consistent deployment environments
CI/CD	GitHub Actions	Automated testing and deployment

Do not install every tool automatically. Choose a minimal stack appropriate to your application's complexity.

2. Dependency Management with uv

Use uv instead of manually combining pip, venv, and dependency files for routine project management.

Create a project
bash
uv init my-app
cd my-app

Add dependencies
bash
# Runtime dependencies
uv add fastapi pydantic-settings

# Development dependencies
uv add --dev pytest pytest-cov ruff mypy

Run commands
bash
uv run python -m my_app
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy src

Synchronize dependencies
bash
# Resolve and update the lockfile when dependencies change
uv lock

# Install the locked dependencies
uv sync --locked

# Include development dependencies
uv sync --locked --all-groups

Dependency management rules
Commit pyproject.toml and uv.lock to Git.
Never commit .venv/.
Use uv add and uv remove to manage dependencies.
Use uv sync --locked in CI to enforce lockfile consistency.
Pin or constrain the supported Python version.
Upgrade dependencies deliberately and run tests after upgrades.
Review security advisories and remove unused dependencies.
Separate runtime dependencies from development-only dependencies.
Use the same locked dependencies across development, CI, and deployment.

Documentation: https://docs.astral.sh/uv/guides/projects/

3. Project Structure

A useful starting structure for a Python API or backend service:

text
my-app/
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
├── .gitignore
├── README.md
├── Dockerfile
├── src/
│   └── my_app/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── api/
│       ├── services/
│       ├── repositories/
│       ├── models/
│       └── utils/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
└── .github/
    └── workflows/
        └── ci.yml

Responsibilities
main.py: Application entry point.
config.py: Configuration and settings.
api/: HTTP endpoints and request handling.
services/: Business logic.
repositories/: Database and external data access.
models/: Domain models and validation schemas.
tests/unit/: Isolated unit tests.
tests/integration/: Tests involving real dependencies.
pyproject.toml: Project metadata, dependencies, and tool configuration.
uv.lock: Reproducible dependency resolution.
Dockerfile: Container build instructions.
.github/workflows/: CI automation.

Keep the structure proportional to the application's complexity. Avoid unnecessary abstractions and excessive numbers of tiny modules.

4. Code Quality and Formatting

Use automated tools to maintain consistent, readable, and reliable code.

Ruff
bash
uv run ruff check .
uv run ruff check . --fix
uv run ruff format .
uv run ruff format --check .


Use ruff check . --fix to apply supported automatic lint fixes. Review changes before committing.

Type checking

Choose one primary type checker:

bash
uv run mypy src


Alternatively, configure Pyright.

Gradually add type annotations to public functions, service interfaces, configuration objects, and complex business logic.

Recommended practices
Follow PEP 8 conventions.
Use descriptive names.
Prefer small functions with clear responsibilities.
Avoid mutable global state.
Use context managers for resources.
Avoid broad exception handling.
Add docstrings where they clarify non-obvious behavior.
Use explicit return types for important functions.
Avoid Any when a more precise type is practical.
Avoid unnecessary inheritance and abstractions.
Example
python
def calculate_total(
    prices: list[float],
    tax_rate: float,
) -> float:
    subtotal = sum(prices)
    return subtotal * (1 + tax_rate)


For financial calculations, prefer Decimal over floating-point arithmetic.

5. Testing Strategy

Use pytest as the primary testing framework.

Test categories

Unit tests

Business logic
Input validation
Calculations
Edge cases
Error handling

Integration tests

Database operations
External service integrations
Message queues
Storage systems

API tests

Authentication
Authorization
Request validation
Response schemas
Error responses

Regression tests

Bugs that have previously occurred

End-to-end tests

Critical user workflows across multiple components
Run tests
bash
uv run pytest
uv run pytest --cov=my_app --cov-report=term-missing

Testing rules
Test behavior rather than implementation details.
Test important failure cases, not just successful cases.
Use fixtures for shared setup.
Mock external boundaries when appropriate.
Keep integration tests for important interactions between real components.
Use a dedicated test database.
Avoid tests that depend on execution order.
Do not rely exclusively on code coverage percentages.

Prioritize high-risk business logic, authentication, permissions, data integrity, and payment or billing workflows.

Documentation: https://docs.pytest.org/

6. Configuration and Secrets

Never hardcode credentials or environment-specific configuration in source code.

Example configuration
python
# src/my_app/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str
    api_key: str


settings = Settings()


Install the settings dependency:

bash
uv add pydantic-settings

Configuration rules
Use environment variables for deployment-specific settings.
Maintain .env.example with placeholder values.
Add .env to .gitignore.
Never commit real API keys, tokens, or passwords.
Validate required configuration at startup.
Use a secrets manager in production.
Never log secret values.
Use different credentials for development, staging, and production.

Keep application configuration separate from business logic.

7. Logging and Observability

Production applications need useful information when something fails.

Logging practices
Use Python's standard logging module or structlog.
Prefer structured logs for services that need centralized log analysis.
Include timestamps, severity, service name, and request IDs.
Record unexpected exceptions with stack traces.
Log important business and operational events.
Avoid logging credentials, access tokens, or sensitive personal data.
Use appropriate log levels: DEBUG, INFO, WARNING, ERROR, and CRITICAL.
Monitoring practices

Monitor:

Request latency
Error rates
Request throughput
CPU and memory usage
Database connection usage
Queue depth and processing failures
External API latency and errors

Use OpenTelemetry when distributed tracing or standardized instrumentation is useful.

Add health endpoints when appropriate:

/health: Indicates whether the process is responsive.
/ready: Indicates whether the service is ready to handle traffic.

Do not expose sensitive infrastructure details through public health endpoints.

8. Security Best Practices

Security must be part of development and deployment.

Application security
Validate all external inputs.
Enforce authentication and authorization.
Use parameterized SQL queries or a safe ORM.
Set request size limits and timeouts.
Apply rate limits where appropriate.
Avoid exposing stack traces to API clients.
Keep dependencies updated.
Scan dependencies for known vulnerabilities.
Use least-privilege credentials.
Use HTTPS in production.
Restrict access to administrative endpoints.
Validate uploaded files and enforce size limits.
Dependency and source scanning
bash
uv add --dev bandit pip-audit

uv run bandit -r src
uv run pip-audit


Run security checks in CI and review findings before deployment.

Git security
Keep secrets out of source code.
Protect the main branch.
Review dependency changes.
Use secret scanning where available.
Never store production credentials in test fixtures.
Rotate credentials if they are accidentally exposed.

Remember that authentication identifies a user, while authorization determines what that user is allowed to do.

9. Database Best Practices

For PostgreSQL or another relational database:

Use Alembic or an equivalent migration tool.
Keep schema changes under version control.
Use transactions for operations that must succeed or fail together.
Configure connection pooling.
Set query and connection timeouts.
Add indexes based on actual query patterns.
Avoid N+1 queries.
Validate data at appropriate application boundaries.
Back up important data.
Test restoration procedures.
Use separate databases or credentials for tests and production.
Apply migrations as a controlled deployment step.

Do not rely on automatic table creation at application startup as your production migration strategy.

For slow or long-running tasks, use a background job system when appropriate rather than holding an HTTP request open indefinitely.

10. Docker and CI/CD

Docker can provide consistent environments across development, testing, and production.

Container best practices
Use a suitable, maintained base image.
Use multi-stage builds when useful.
Run the application as a non-root user.
Avoid copying .env files and secrets into images.
Keep images small.
Separate development dependencies from runtime dependencies.
Use a .dockerignore file.
Configure health checks appropriately.
Handle termination signals and graceful shutdown.
Scan built images for vulnerabilities.
Continuous integration

A CI pipeline should normally run:

Dependency and lockfile validation.
Linting.
Formatting verification.
Type checking.
Unit and integration tests.
Security checks.
Build verification.
Example GitHub Actions workflow
yaml
name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v6

      - run: uv sync --locked --all-groups

      - run: uv run ruff check .

      - run: uv run ruff format --check .

      - run: uv run mypy src

      - run: uv run pytest


Before using this in production: Pin third-party GitHub Actions to trusted full commit SHAs, review action permissions, and configure any required services and secrets.

Deployment best practices
Test before deploying.
Deploy to staging before production when appropriate.
Use controlled database migrations.
Configure readiness and health checks.
Monitor errors after deployment.
Keep the previous working release available when feasible.
Have a documented rollback procedure.
11. AI-Agent Production Practices

AI-agent applications require additional safeguards because model outputs and tool decisions are not inherently trustworthy.

Tool permissions
Give agents only the tools they need.
Enforce permissions in application code.
Require approval for sensitive or destructive actions.
Never let a model override authorization rules.
Restrict access to files, databases, and external services.
Execution limits
Set request and tool-call timeouts.
Limit the number of agent steps.
Configure maximum token budgets.
Track model and tool costs.
Limit concurrency.
Prevent unbounded retries and recursive execution.
Output validation
Validate structured model outputs with Pydantic.
Treat generated SQL, shell commands, URLs, and file paths as untrusted.
Apply allowlists where appropriate.
Validate tool arguments before execution.
Never execute arbitrary model-generated code without a secure, explicitly designed execution boundary.
Reliability
Use bounded retries with backoff and jitter.
Use idempotency keys for operations that must not execute twice.
Persist job state for workflows that need recovery.
Handle partial failures.
Use durable queues for long-running tasks when appropriate.
Make external operations safe to retry whenever possible.
Evaluation and monitoring

Maintain a dataset of representative tasks and measure:

Task success rate
Tool-call accuracy
Invalid output rate
Latency
Token usage and cost
Failure and retry rates
Safety and permission violations

Run evaluations when changing models, prompts, tools, or orchestration logic.

Record relevant model and prompt versions, tool calls, timings, and outcomes. Redact sensitive data and restrict access to traces.

Human approval

Use human approval for high-impact actions such as:

Sending sensitive communications
Deleting important data
Making financial transactions
Changing production infrastructure
Performing irreversible operations
12. Daily Development Workflow
Step 1: Start a task
Create a feature branch.
Understand the expected behavior.
Identify affected components and potential risks.
Step 2: Implement the change
Keep the change focused.
Separate business logic from external integrations where useful.
Add or update tests.
Step 3: Run local checks
bash
uv run ruff check . --fix
uv run ruff format .
uv run mypy src
uv run pytest


Review automatically applied fixes before committing.

Step 4: Review the code

Check:

Correctness and edge cases
Error handling
Security implications
Configuration and secrets
Performance implications
Dependency changes
Test quality
Step 5: Open a pull request

Let CI run the checks independently of the local environment.

Require review for important changes and protect the main branch.

Step 6: Deploy safely
Deploy a tested build.
Apply controlled migrations.
Verify service health.
Monitor errors and latency.
Roll back if necessary.
13. Production Readiness Checklist
Project setup
Use uv, pyproject.toml, and a committed uv.lock.
Define supported Python versions.
Use a clear project structure.
Add a README and .gitignore.
Provide .env.example.
Document installation and development commands.
Code quality
Configure Ruff.
Configure mypy or Pyright.
Add automated tests with pytest.
Test important error cases.
Add pre-commit hooks or equivalent local checks.
Review dependency changes.
Configuration and security
Validate configuration at startup.
Protect secrets.
Enforce authentication and authorization.
Configure timeouts and appropriate rate limits.
Scan dependencies for known vulnerabilities.
Avoid exposing sensitive information in logs or errors.
Database and reliability
Version-control database migrations.
Configure transactions and connection management.
Define retry and timeout policies.
Back up important data.
Test recovery and restoration procedures.
Deployment and operations
Add CI checks.
Build and verify deployment artifacts.
Use secure container configuration when using Docker.
Add logging and monitoring.
Configure health and readiness checks.
Document rollback procedures.
Verify the production deployment after release.
AI-agent applications
Restrict tool permissions.
Validate model-generated outputs.
Configure execution and cost limits.
Use bounded retries and idempotency where necessary.
Add evaluations for representative tasks.
Trace executions and tool calls.
Require approval for sensitive operations.
14. Useful Documentation
uv: https://docs.astral.sh/uv/
Ruff: https://docs.astral.sh/ruff/
pytest: https://docs.pytest.org/
mypy: https://mypy.readthedocs.io/
Pyright: https://microsoft.github.io/pyright/
Pydantic: https://docs.pydantic.dev/
FastAPI: https://fastapi.tiangolo.com/
Alembic: https://alembic.sqlalchemy.org/
Bandit: https://bandit.readthedocs.io/
pip-audit: https://github.com/pypa/pip-audit
OpenTelemetry: https://opentelemetry.io/docs/
Docker: https://docs.docker.com/
GitHub Actions: https://docs.github.com/en/actions
Final Recommendations

Prioritize these practices in order:

Reproducibility: Use uv, lock dependencies, and define supported Python versions.
Code quality: Configure Ruff, type checking, and automated tests.
Reliability: Validate configuration, handle errors, and set timeouts.
Security: Protect secrets, validate inputs, and enforce authorization.
Deployment: Automate CI, use controlled releases, and maintain rollback options.
Observability: Monitor logs, errors, latency, and resource usage.
AI-agent safeguards: Restrict tool permissions, evaluate behavior, and control execution costs.

The goal is not to use the largest possible collection of tools. It is to build a small, consistent engineering workflow that makes the application easy to maintain, test, deploy, debug, and secure.