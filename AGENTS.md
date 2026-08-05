# Repository Guidelines

TestWise — Pytest-based API automation framework (Python 3.12, uv). Tests are data-driven: Python files provide structure; YAML files supply requests, parameters, and assertions.

## Project Structure & Module Organization

- `base/` — framework core: `apiutil.py` (`RequestBase` engine), `sendrequest.py`, `generateId.py`.
- `common/` — utilities (`readyaml.py`, `assertions.py`, `connection.py`, `recordlog.py`), data factory (`data_factory.py`), perf stats (`perf_stats.py`), contract check (`schema_check.py`), AI analysis agent (`ai_agent.py` + `ai_tools.py` + `ai_report.py`).
- `conf/` — `setting.py` (paths, log levels, `REPORT_TYPE`) and `config.ini` (hosts, credentials).
- `testcase/` — tests plus YAML data, grouped by module: `ProductManager/`, `Single interface/`, `Business interface/`.
- `data/` — test data; `mock_server/` — Flask mock API on `127.0.0.1:8787`; `perf/` — Locust load tests; `docs/` — requirement-case mapping; `.github/` + `Jenkinsfile` — CI.
- `report/` — all generated artifacts: reports, coverage, logs, AI report, mock server logs, and the `extract.yaml` runtime store.

## Build, Test, and Development Commands

- `uv sync` — install dependencies.
- `python run.py` — run suite, report, AI analysis; `[PARALLEL]` enables xdist with retries and coverage.
- `python run.py --analyze` — analyze the existing report without rerunning tests.
- `pytest ./testcase -vs` — direct run; add `-n auto`, `--reruns 2`, `--cov` as needed.
- `cd perf && locust -f locustfile.py --host=http://127.0.0.1:8787` — load test.
- `pre-commit run --all-files` — lint and format (ruff).

## Coding Style & Naming Conventions

- PEP 8, 4-space indentation, `snake_case` functions, `PascalCase` classes; Chinese comments/docstrings are the norm.
- Test files `test_*.py`, classes `Test*`, methods `test_*`; name YAML files after the API under test.
- Format with `ruff format`, lint with `ruff check`; keep secrets out of code and `config.ini`.

## Testing Guidelines

- pytest, allure-pytest, pytest-ordering, pytest-xdist, pytest-rerunfailures.
- Parametrize with `get_testcase_yaml()`; declare assertions in YAML `validation:` (`contains`, `eq`, `ne`, `rv`, `db`, `schema`).
- Mock data is backed up and restored by the master process each session; use `data_factory.py` for unique data.
- Track coverage in `report/coverage` and traceability in `docs/requirement_case_mapping.md`; no hard gate.

## Commit & Pull Request Guidelines

- Short imperative summaries with optional scope prefixes (`docs(README): ...`, `fix: ...`); Chinese or English accepted.
- PRs: describe what and why, link issues, attach evidence (Allure, results.xml, coverage, ai_report.html); screenshots for UI/mock changes.

## Agent-Specific Instructions

- Read `conf/setting.py` and `pytest.ini` first; start the mock server before tests.
- Sensitive values via env vars (`AI_API_KEY`, `ZQ_*`); never commit real credentials.
- AI analysis runs automatically after `run.py`; the report is `report/ai_report.html`.
