# The dashboard — explained

**Owner:** MD · **Read after:** `05-api-explained.md` · **Code:** `frontend/`

---

## 1. What it is

Three files — `index.html`, `style.css`, `app.js` — plus a `config.js` written at deploy time. No framework, no build step, no dependencies. About 250 lines of JavaScript that any teammate can read in one sitting.

**It holds no data of its own.** Everything on screen arrives from the API, which refuses to answer without a valid token. That is precisely why the page can sit in a public S3 bucket safely: the bucket contains the page *shell*, not campus data.

## 2. Frontend vs backend

| | Backend | Frontend |
|---|---|---|
| Runs on | AWS Lambda | the user's browser |
| Written in | Python | HTML, CSS, JavaScript |
| Can be trusted? | **Yes** — we control it | **No** — anyone can edit it |
| Decides severity? | **Yes** | No, it only displays it |

The third row is the one that matters. A user can open developer tools and change anything on this page. So the page is never allowed to *decide* anything that matters — it displays what the API says. Hiding the alerts panel from `staff` is a convenience, not a security control; the security control is the API returning 403.

## 3. The flow

```text
  sign in ──► POST /login ──► token ──► sessionStorage
                                           │
         every 10s  ┌────────────────────┬─┴──────────────────┐
                    ▼                    ▼                    ▼
               GET /stats          GET /events          GET /alerts
                    │                    │                    │
              tiles + bars         events table         alerts panel
```

`Promise.all` fires the three calls in parallel, so a refresh takes as long as the slowest one rather than the sum of all three.

## 4. Where the token lives — an honest trade-off

`sessionStorage`. It survives a page refresh (an accidental F5 mid-demo does not log you out) and is cleared when the tab closes.

The safer option is a plain JavaScript variable: no script could read it back, but every refresh loses the session. We chose convenience here and put the real mitigations elsewhere — the token lasts one hour, this page loads **no third-party scripts at all**, and no secret is ever placed inside a JWT.

Worth being able to state plainly, because "why is the token in storage?" is a fair question and "we considered it and here is the trade" is a much better answer than "that is how it is usually done".

Every storage call is wrapped in try/catch: in a private window or with site data blocked, these throw, and a dashboard that cannot remember a token should still work.

## 5. Colour is assigned by job, never by taste

This is the part worth understanding, because it is a method rather than an opinion.

| The job | Encoding | Where |
|---|---|---|
| **Magnitude** — how much | one sequential blue hue, light → dark | energy bars, occupancy under capacity |
| **State** — what kind | the reserved status palette | normal / warning / critical |

Two rules follow:

**Status colours are reserved.** Green, amber and red mean normal, warning and critical — and never "the third building". If they doubled as series colours, a red bar would be ambiguous.

**Colour never carries meaning alone.** Every coloured mark sits beside a written severity word and a text glyph (`!!`, `!`). This is an accessibility requirement — roughly one man in twelve has some colour-vision deficiency — and it is also the documented mitigation for amber sitting below 3:1 contrast on a light background.

The three status colours were checked with a palette validator in both light and dark mode: worst adjacent CVD separation ΔE 11.3, worst normal-vision separation ΔE 27.6, both comfortably past their thresholds.

**Dark mode is a selected set of values, not an inverted one.** The blues are re-stepped for the dark surface so they stay legible on it.

## 6. Reading the bars

```text
Library-A / A203  CRITICAL           58 of 45 · 129%
████████████████████████████████████████            ← red, over 120%

Sports-D / D002   WARNING            44 of 40 · 110%
████████████████████████████████████                ← amber, over 100%

Science-B / B110                     51 of 60 · 85%
██████████████████████████                          ← blue, under capacity
```

The thresholds are the same ones the server uses, so a bar and an alert can never disagree. Bars are thin, anchored to the baseline, with a 4px rounded data-end — the conventions that keep a chart readable rather than decorative.

Energy bars are a single series, so there is no legend: the heading names what they are, and every bar is directly labelled with its value, which replaces an axis on a five-bar chart.

## 7. Polling is a cost decision

At 10-second intervals a tab open all day makes roughly **17,000 requests**. Against a pay-per-request API that is exactly the quiet spend the brief warns about. So:

- polling stops while the tab is hidden (`document.hidden`),
- polling pauses after **15 idle minutes**, with a visible notice and a Refresh button to resume.

Both thresholds live in `config.js`. This is what "cost awareness" looks like in code rather than in a paragraph.

## 8. Error handling

| Situation | What the page does |
|---|---|
| 401 on any call | Clears the token and returns to sign-in: "Your session expired" |
| 403 on `/alerts` | The panel is hidden for `staff` before the call is made |
| Network failure | A banner, and it retries on the next poll — it does not crash |
| `truncated: true` in `/stats` | A banner saying the statistics cover a partial day |
| Wrong credentials | Shows the server's message **unchanged** — the same text for wrong password and unknown user, so this form cannot be used to discover which emails have accounts |

## 9. One bug worth keeping in the report

The first render had the sign-in form showing *underneath* the dashboard, even though the code sets `hidden`.

Cause: the browser's own stylesheet says `[hidden] { display: none }`, but any explicit `display:` rule of ours beats it — and `.login-view { display: grid }` silently cancelled the attribute. The fix is one line, `[hidden] { display: none !important; }`.

It is worth recording because of **how it was found**: by rendering the page and looking at it. No test would have caught it; the elements existed, the JavaScript ran without error, and the attribute was set correctly. Some classes of bug only exist visually.

---

## Can you explain this?

1. Why can this page sit in a public S3 bucket without exposing campus data?
2. Hiding the alerts panel from `staff` — is that a security control?
3. Why is a severity word printed next to every coloured mark?
4. Why does polling stop when the tab is hidden?
5. Where is the token kept, and what is the trade-off?

### Answers

1. Because the bucket contains only HTML, CSS and JavaScript — the page shell. Every piece of data is fetched from the API, which refuses any request without a valid Cognito token.
2. No. It is a convenience so staff are not shown a panel that would only error. The security control is the API returning 403 — a user who edits the page in developer tools still gets nothing.
3. So colour never carries meaning on its own: for colour-blind readers, printed in greyscale, or on a projector with poor colour. It is also the documented mitigation for amber's low contrast on a light background.
4. Cost. Ten-second polling with a tab open all day is roughly 17,000 requests against a pay-per-request API, and nobody is reading a hidden tab. It also pauses after 15 idle minutes.
5. `sessionStorage` — it survives a refresh and clears when the tab closes. The safer alternative is an in-memory variable, which loses the session on every refresh; we traded that for a one-hour token lifetime and a page that loads no third-party scripts.
