
# Python production practices


- Preserve the existing stack; use `uv`, `pyproject.toml`, and a committed `uv.lock`. Use `uv sync --locked --all-groups` to reproduce an environment. Do not install every tool listed in the reference.
- Keep domain logic separate from external I/O. Use descriptive functions, type annotations at public boundaries, explicit configuration, and context managers.
- Run Ruff, the configured type checker, and behavior-focused pytest checks. Test malformed inputs, data integrity, failed dependencies, and relevant integration boundaries.
- Validate external inputs and settings; keep secrets outside Git and logs. Add timeouts and bounded retries to actual external calls.
- Add migrations, authentication, observability, container hardening, and CI when those components exist; do not add unnecessary infrastructure to a local teaching script.
- For synthetic-data work, record seeds and assumptions, split by independent experiment, fit preprocessing only on training data, select on validation, and reserve test data for reporting. Do not describe synthetic accuracy as real-world validation.
- Report commands actually executed and unresolved limits. Preserve user scope and existing permissions.
