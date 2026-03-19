# Zakera Load Tests

This directory contains [Locust](https://locust.io) load-testing scenarios
for the Zakera AI Chat Agent API.

## Quick Start (local)

```bash
# 1. Install dependencies
pip install -r requirements-loadtest.txt

# 2. Start the Zakera API locally
make dev

# 3. Run Locust in interactive mode
locust --locustfile tests/load/locustfile.py --host http://localhost:8000

# 4. Open http://localhost:8089, set users/spawn-rate, and click Start
```

## Headless (CI) Mode

```bash
locust \
  --locustfile tests/load/locustfile.py \
  --host http://staging.yourapp.com \
  --users 50 \
  --spawn-rate 5 \
  --run-time 5m \
  --headless \
  --csv report
```

This generates `report_stats.csv`, `report_failures.csv`, and
`report_stats_history.csv` in the current directory.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LOCUST_API_TOKEN` | _(empty)_ | Pre-minted JWT — skips the login step |
| `LOCUST_USERNAME` | `loadtest@zakera.ai` | Username for `/auth/token` |
| `LOCUST_PASSWORD` | `LoadTest123!` | Password for `/auth/token` |
| `LOCUST_SKIP_AUTH` | `false` | Skip auth entirely (open staging envs) |

## Task Weights

| Task | Weight | Endpoint |
|---|---|---|
| Send chat message | 40 % | `POST /api/v1/conversations/:id/messages` |
| List conversations | 20 % | `GET /api/v1/conversations` |
| Get conversation | 15 % | `GET /api/v1/conversations/:id` |
| Generate summary | 10 % | `POST /api/v1/conversations/:id/summary` |
| Health check | 10 % | `GET /health` |
| Export conversation | 5 % | `GET /api/v1/conversations/:id/export` |

## Performance Thresholds (CI Gate)

The nightly CI workflow (`.github/workflows/nightly-load-test.yml`) **fails**
the build when:

- **p95 response time > 2 000 ms** — measured on the _Aggregated_ row of
  `report_stats.csv`
- **Error rate > 1 %** — (failure count / total request count) × 100

Adjust these thresholds in the workflow YAML if your SLA differs.

## Viewing the HTML Report

After a headless run with `--html report.html`, open the file in any browser.
Key sections:

- **Charts** — RPS, response time percentiles, and user count over time
- **Statistics** — min/avg/max/p50/p95/p99 per endpoint
- **Failures** — full error messages and counts

## Tips

- Increase `--users` gradually (e.g., 10 → 50 → 100) to find the saturation
  point before the API error rate spikes.
- Use `--spawn-rate 1` for a gentle warm-up when testing against a cold
  staging environment with autoscaling.
- Set `LOCUST_SKIP_AUTH=true` when the staging environment is behind a
  shared API gateway that handles auth separately.
