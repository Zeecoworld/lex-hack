# AI Bias & Safety Auditor — LexHack Scaffold

Runs the same decision prompt (loan approval, resume screening, pretrial
risk score) through an LLM with only the applicant's name/neighborhood
swapped, then charts how much the model's answers shift by demographic
group.

## Structure
```
backend/    FastAPI service — scenarios, swap engine, scoring, /audit endpoint
frontend/   Next.js dashboard — scenario picker, live run button, charts
```

## Backend setup
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```
Visit `http://localhost:8000/docs` for interactive API docs.

## Frontend setup
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```
Visit `http://localhost:3000`.

## How it works
1. `app/scenarios.py` defines each prompt template plus the swap values
   (names, neighborhoods) grouped by demographic label.
2. `app/audit_engine.py` expands the swap sets into concrete prompts
   (cross-product, capped/sampled at `max_variants`), runs them through
   the model via `app/llm_client.py`.
3. `app/scoring.py` parses each response into a numeric score (approve/deny
   → 1/0, or a 1–10 risk number) and computes the gap between group means —
   the "disparity score" shown on the dashboard.
4. The frontend calls `POST /audit`, then charts `disparities` per swap
   dimension (e.g. by name-group, by neighborhood).

## Model in use
`gemini-3.8-flash`. This is a "thinking" model, so on harder prompts it may
run extra reasoning steps before answering — per-call latency/token usage
can be a bit higher than older Flash models. Scoring in `app/scoring.py`
only looks at the final text, so this doesn't affect correctness, just run
time. To try a different model, change the default in `app/llm_client.py`
and `app/models.py` (backend) and `lib/api.ts` (frontend).

## Known simplifications (say this in your Devpost writeup)
- Name choice is used as a *proxy* for perceived demographic signaling —
  a standard, imperfect technique from audit-study literature (e.g.
  Bertrand & Mullainathan), not a claim about the named individuals.
- Scoring is intentionally simple (substring/regex matching) so the
  scoring step itself stays auditable — a black-box scorer would
  undermine the pitch of the tool.
- `RUN_STORE` in `main.py` is in-memory. Wire in Supabase (see
  `.env.example`) for persistence across runs/demo restarts.

## Deploying to Render

This repo includes a `render.yaml` Blueprint that provisions both services
at once.

1. Push this folder to a GitHub repo.
2. In Render: **New → Blueprint**, point it at the repo. Render reads
   `render.yaml` and creates two web services:
   - `bias-auditor-backend` (FastAPI, free plan)
   - `bias-auditor-frontend` (Next.js, free plan)
3. Render will pause and ask you to fill in the two `sync: false` values:
   - Backend service → `GEMINI_API_KEY` → your real Gemini key
   - Frontend service → `NEXT_PUBLIC_API_BASE` → leave blank for now, deploy,
     then come back once you have the backend's URL (step 4)
4. Once the backend finishes deploying, copy its URL (something like
   `https://bias-auditor-backend.onrender.com`), set it as the frontend's
   `NEXT_PUBLIC_API_BASE`, and trigger a manual redeploy of the frontend
   (env vars are baked in at build time for `NEXT_PUBLIC_*` vars, so a
   redeploy is required after changing this one).
5. Optional but recommended once both URLs exist: set the backend's
   `ALLOWED_ORIGINS` to the frontend's exact URL instead of `*`, then
   redeploy the backend too.

Free-plan services spin down after inactivity, so the first request after
idling (including your first test) can take ~30-50s to wake up — don't
mistake that for a hang.

## Suggested demo flow
1. Show the scenario cards → explain the "identical profile, name swapped"
   design.
2. Click "Run live audit" on Resume Screening → let the audience watch it
   run against the real API.
3. Point at the bar chart gap and read the headline disparity score.
4. Open the raw outputs panel to show the actual model text behind the
   numbers — this is what makes it feel auditable, not just a chart.

## Next steps to extend
- Add a second model (e.g. Claude or OpenAI) for side-by-side cross-model comparison.
- Persist runs to Supabase and show a history/trend view.
- Let judges/users paste their own prompt template + swap list instead of
  only the 3 pre-built scenarios.
