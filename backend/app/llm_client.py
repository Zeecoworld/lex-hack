"""
Wrapper around the model-under-test. Kept separate from the audit engine
so swapping providers later (or adding a second one for cross-model
comparison) is a one-file change.

Uses the Gemini API (google-genai SDK). Individual call failures (rate
limits, transient network errors) are retried with backoff and, if still
failing, converted into an error marker string rather than raised — one
flaky call should never take down an entire audit run.
"""
import asyncio
import os

from google import genai
from google.genai import errors as genai_errors

_client: genai.Client | None = None

ERROR_MARKER = "[NO RESPONSE - request failed after retries]"


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not set. Copy .env.example to .env and fill it in."
            )
        _client = genai.Client(api_key=api_key)
    return _client


async def _call_once(prompt: str, model: str, max_tokens: int) -> str:
    client = get_client()
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=model,
        contents=prompt,
        config={"max_output_tokens": max_tokens},
    )
    return response.text or ""


async def run_prompt(
    prompt: str,
    model: str = "gemini-3.8-flash",
    max_tokens: int = 200,
    max_retries: int = 3,
) -> str:
    """
    Send a single prompt to the model-under-test. Retries on rate limits
    (429) and transient server errors (5xx) with exponential backoff.
    Returns ERROR_MARKER instead of raising if every attempt fails, so
    the audit engine can still score every other variant in the batch.
    """
    delay = 1.5
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return await _call_once(prompt, model, max_tokens)
        except genai_errors.ClientError as e:
            # 429 (rate limit) is worth retrying; other 4xx (bad key, bad
            # model name) will just fail the same way again, so bail fast.
            last_error = e
            if getattr(e, "code", None) != 429:
                break
        except Exception as e:  # noqa: BLE001 - deliberately broad: any transient failure
            last_error = e
        if attempt < max_retries - 1:
            await asyncio.sleep(delay)
            delay *= 2
    print(f"[llm_client] giving up on prompt after {max_retries} attempts: {last_error}")
    return ERROR_MARKER


async def run_prompts_batch(prompts: list[str], model: str, max_concurrency: int = 3) -> list[str]:
    """
    Run many prompts with bounded concurrency. Concurrency is kept
    deliberately low (default 3) to stay under free-tier Gemini rate
    limits during a demo; a single slow/failed call never aborts the
    rest of the batch (see run_prompt's own retry/fallback handling).
    """
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _run(p: str) -> str:
        async with semaphore:
            return await run_prompt(p, model=model)

    return await asyncio.gather(*(_run(p) for p in prompts))
