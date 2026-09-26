"""
FastAPI entrypoint. Run with:
    uvicorn app.main:app --reload --port 8000

Endpoints:
    GET  /scenarios              -> list pre-built scenarios
    GET  /scenarios/{id}         -> scenario detail (template, swap sets)
    POST /audit                  -> run a live audit, returns full result
"""
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.audit_engine import run_audit
from app.models import AuditRunRequest, AuditRunResult, Scenario
from app.scenarios import ALL_SCENARIOS

app = FastAPI(title="LexHack Bias Auditor", version="0.1.0")

# Comma-separated list of allowed origins, e.g.
# "https://bias-auditor-frontend.onrender.com,http://localhost:3000".
# Defaults to "*" so local dev / initial demo deploys work with zero config.
_origins_env = os.environ.get("ALLOWED_ORIGINS", "*")
_allowed_origins = ["*"] if _origins_env.strip() == "*" else [
    o.strip() for o in _origins_env.split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


import traceback


def _error_response(request: Request, exc: Exception) -> JSONResponse:
    print(f"[error] {request.method} {request.url.path}: {exc!r}")
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"detail": f"Internal error: {exc}"})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Last-resort safety net for exceptions raised before route bodies even
    run (e.g. request validation plumbing). NOTE: this alone is NOT enough
    to fix CORS on errors — a handler registered for the base `Exception`
    class attaches to Starlette's outermost ServerErrorMiddleware, which
    sits *outside* CORSMiddleware in the stack, so its response never
    passes back through CORSMiddleware to get the Access-Control headers
    added. The browser then can't read the (CORS-less) error response at
    all and reports it as a generic "Failed to fetch" instead of showing
    the real 500. The actual fix is the try/except inside each route body
    below — that keeps the error response inside the normal stack, where
    CORSMiddleware still processes it. This handler just covers anything
    that manages to escape before reaching a route.
    """
    return _error_response(request, exc)

# In-memory run store for the demo (swap for Supabase persistence — see
# supabase_store.py stub — once you're past the hackathon prototype stage).
RUN_STORE: dict[str, AuditRunResult] = {}


@app.get("/scenarios", response_model=list[Scenario])
def list_scenarios():
    return list(ALL_SCENARIOS.values())


@app.get("/scenarios/{scenario_id}", response_model=Scenario)
def get_scenario(scenario_id: str):
    scenario = ALL_SCENARIOS.get(scenario_id)
    if not scenario:
        raise HTTPException(404, f"Unknown scenario_id: {scenario_id}")
    return scenario


@app.post("/audit", response_model=AuditRunResult)
async def create_audit(req: AuditRunRequest, request: Request):
    scenario = ALL_SCENARIOS.get(req.scenario_id)
    if not scenario:
        raise HTTPException(404, f"Unknown scenario_id: {req.scenario_id}")

    # Caught here (not left to propagate) so the error response still goes
    # through CORSMiddleware normally — see the long comment above on why
    # that matters. In practice llm_client's own retry/fallback logic means
    # this should rarely trigger; it's the backstop for anything it misses
    # (bad/missing API key, scenario bugs, etc).
    try:
        result = await run_audit(
            scenario=scenario,
            model=req.model,
            max_variants=req.max_variants,
            repeats=req.repeats,
        )
    except Exception as exc:  # noqa: BLE001 - intentionally broad, see comment above
        return _error_response(request, exc)

    RUN_STORE[result.run_id] = result
    return result


@app.get("/audit/{run_id}", response_model=AuditRunResult)
def get_audit(run_id: str):
    result = RUN_STORE.get(run_id)
    if not result:
        raise HTTPException(404, f"Unknown run_id: {run_id}")
    return result


@app.get("/health")
def health():
    return {"status": "ok"}
