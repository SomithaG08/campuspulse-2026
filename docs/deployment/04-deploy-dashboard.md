# Deploying the Dashboard (Phase 9)

The backend must be deployed first — the dashboard is useless without an API to call.

## Deploy

```bash
bash scripts/deploy-dashboard.sh
```

It reads `terraform output`, writes `config.js` with your real API endpoint into `frontend/.build/`, and syncs that folder to the S3 bucket. The source `frontend/config.js` keeps its placeholder, so `git status` stays clean and nobody accidentally commits one person's endpoint.

Then open the URL it prints.

## Verify

| Check | Expected |
|---|---|
| Page loads | Sign-in form, no console errors |
| Sign in as `ops@` | Dashboard appears, tiles populate |
| Start the simulator | Numbers rise within ~10 s |
| `python simulator.py --force-alert -n 1` | A red row appears in Active alerts |
| Sign in as `staff@` | **The alerts panel is absent** — staff get 403 there |
| Leave it 15 minutes | Footer: "Auto-refresh paused to save cost" |

The fifth row is the one to screenshot: the same page showing different things to different roles is the clearest evidence for the brief's two-role requirement.

## If the page is blank or empty

| Symptom | Cause | Fix |
|---|---|---|
| "config.js has no API endpoint yet" | The script did not run, or you opened `frontend/index.html` directly | Run the deploy script, open the S3 URL |
| Console: "blocked by CORS policy" | The API's CORS settings | `cors_configuration` in `apigateway.tf`; `curl` works regardless, so this is browser-only |
| Sign in fails with "Could not reach the API" | Wrong endpoint, or the API is not deployed | `curl $API/health` |
| Tiles show `–` forever | `/stats` returning non-200 | Browser devtools → Network, then the `cp-stats` log group |
| Alerts panel missing | You signed in as `staff` | Correct behaviour |
| 403 in the console on `/alerts` | Same | Correct behaviour |

## Cost note

The dashboard polls `/stats`, `/events` and `/alerts` every 10 seconds — about 1,080 requests an hour with a tab open. Well inside the free tier for demo use, but it is why polling stops when the tab is hidden and pauses after 15 idle minutes. **Close the tab when you are done.**
