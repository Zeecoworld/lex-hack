const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export interface Scenario {
  id: string;
  title: string;
  description: string;
  prompt_template: string;
  output_type: "binary_decision" | "risk_score";
  swap_sets: { placeholder: string; values: { value: string; group: string }[] }[];
}

export interface GroupDisparity {
  placeholder: string;
  group: string;
  n: number;
  mean_score: number;
  approval_rate: number | null;
}

export interface VariantResult {
  variant_id: string;
  filled_prompt: string;
  groups: Record<string, string>;
  raw_outputs: string[];
  parsed_scores: (number | null)[];
}

export interface AuditRunResult {
  run_id: string;
  scenario_id: string;
  model: string;
  created_at: string;
  variants: VariantResult[];
  disparities: GroupDisparity[];
  disparity_score: number;
  notes: string;
}

async function readErrorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // response wasn't JSON — fall through to the generic message
  }
  return `Request failed (${res.status})`;
}

/**
 * Wraps fetch so a raw network failure (backend unreachable, CORS
 * blocked, DNS, timeout) gets turned into a message that actually tells
 * the person what to check, instead of the browser's bare
 * "TypeError: Failed to fetch".
 */
async function safeFetch(url: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch {
    throw new Error(
      `Could not reach the API at ${API_BASE}. If it's on Render's free ` +
        `tier it may be waking up (30-50s) — try again in a moment. ` +
        `Otherwise check NEXT_PUBLIC_API_BASE and the backend's ALLOWED_ORIGINS.`
    );
  }
}

export async function listScenarios(): Promise<Scenario[]> {
  const res = await safeFetch(`${API_BASE}/scenarios`);
  if (!res.ok) throw new Error(await readErrorDetail(res));
  return res.json();
}

export async function runAudit(
  scenarioId: string,
  opts: { model?: string; max_variants?: number; repeats?: number } = {}
): Promise<AuditRunResult> {
  const res = await safeFetch(`${API_BASE}/audit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      scenario_id: scenarioId,
      model: opts.model ?? "gemini-3.8-flash",
      max_variants: opts.max_variants ?? 24,
      repeats: opts.repeats ?? 1,
    }),
  });
  if (!res.ok) throw new Error(await readErrorDetail(res));
  return res.json();
}
