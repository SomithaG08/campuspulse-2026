# Dashboard

Three files, no framework, no build step, no dependencies.

| File | What it is |
|---|---|
| `index.html` | Structure: sign-in form, KPI tiles, alerts, occupancy, energy, events table |
| `style.css` | All styling, including dark mode. Colour is assigned by job: sequential blue for magnitude, the reserved status palette for state |
| `app.js` | ~250 lines: login, polling, rendering, error handling |
| `config.js` | API endpoint and polling settings — **rewritten at deploy time**, never edited by hand |

```bash
bash scripts/deploy-dashboard.sh    # writes config.js, syncs to S3
```

Opening `index.html` directly from disk shows "config.js has no API endpoint yet" — that is expected; it needs a deployed API.

Explanation: `docs/learning/15-frontend-explained.md` · Deployment: `docs/deployment/04-deploy-dashboard.md`
