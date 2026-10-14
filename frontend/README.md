# Pages

Three pages, no framework, no build step, no dependencies. One page per role, as asked in the project review (October 2026).

| File | What it is |
|---|---|
| `index.html` | Sign-in. After login it sends administrators to `admin.html` and students to `student.html` |
| `admin.html` + `admin.js` | **Administrator page:** KPI tiles, active alerts, all student requests (urgent first, with who raised them), room occupancy, energy by building, recent events |
| `student.html` + `student.js` | **Student page:** free rooms (most seats first), building comfort, *report a problem* form, *my requests* |
| `app.js` | Shared by all three: API helper, token storage, sign-in, page guard, cost-aware polling |
| `style.css` | All styling, including dark mode. Colour is assigned by job: sequential blue for magnitude, the reserved status palette for state |
| `config.js` | API endpoint and polling settings — the `API_URL` line is **rewritten at deploy time** |

```bash
bash scripts/deploy-dashboard.sh    # writes config.js, syncs all pages to S3
```

PowerShell equivalent: `docs/deployment/06-apply-corrections.md` §5.

The page guard (`requireRole` in `app.js`) only decides what is *shown*. A student who forces their way onto `admin.html` still gets 403 from every admin route: the API decides what is *returned*.

Explanation: `docs/learning/15-frontend-explained.md` · Deployment: `docs/deployment/04-deploy-dashboard.md`
