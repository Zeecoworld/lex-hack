"""
Orchestrates one audit run: expand a scenario's swap sets into concrete
prompt variants, run them through the model-under-test, parse and score
the outputs, and compute disparities.
"""
import itertools
import random
import uuid
from datetime import datetime, timezone

from app.llm_client import run_prompts_batch
from app.models import AuditRunResult, Scenario, VariantResult
from app.scoring import compute_disparities, parse_output


def _expand_variants(scenario: Scenario, max_variants: int) -> list[dict[str, str]]:
    """
    Cross-product of every swap_set's values, each item a dict of
    placeholder -> chosen SwapValue. Cross-products can get large fast
    (e.g. 6 names x 2 neighborhoods = 12) so we cap and randomly sample
    if the full product exceeds max_variants.
    """
    placeholders = [s.placeholder for s in scenario.swap_sets]
    value_lists = [s.values for s in scenario.swap_sets]

    combos = list(itertools.product(*value_lists))
    if len(combos) > max_variants:
        combos = random.sample(combos, max_variants)

    variants = []
    for combo in combos:
        variants.append({ph: sv for ph, sv in zip(placeholders, combo)})
    return variants


async def run_audit(scenario: Scenario, model: str, max_variants: int, repeats: int) -> AuditRunResult:
    combos = _expand_variants(scenario, max_variants)

    filled_prompts: list[str] = []
    variant_meta: list[dict] = []  # parallel to filled_prompts, but one entry per repeat

    for combo in combos:
        fill = {ph: sv.value for ph, sv in combo.items()}
        prompt = scenario.prompt_template.format(**fill)
        groups = {ph: sv.group for ph, sv in combo.items()}
        variant_id = str(uuid.uuid4())[:8]
        for _ in range(repeats):
            filled_prompts.append(prompt)
            variant_meta.append({"variant_id": variant_id, "prompt": prompt, "groups": groups})

    raw_outputs = await run_prompts_batch(filled_prompts, model=model)

    # Regroup repeats back under their variant_id
    grouped: dict[str, VariantResult] = {}
    for meta, output in zip(variant_meta, raw_outputs):
        vid = meta["variant_id"]
        if vid not in grouped:
            grouped[vid] = VariantResult(
                variant_id=vid,
                filled_prompt=meta["prompt"],
                groups=meta["groups"],
                raw_outputs=[],
                parsed_scores=[],
            )
        grouped[vid].raw_outputs.append(output)
        grouped[vid].parsed_scores.append(parse_output(output, scenario))

    variants = list(grouped.values())
    disparities, disparity_score = compute_disparities(variants, scenario)

    return AuditRunResult(
        run_id=str(uuid.uuid4())[:12],
        scenario_id=scenario.id,
        model=model,
        created_at=datetime.now(timezone.utc),
        variants=variants,
        disparities=disparities,
        disparity_score=disparity_score,
        notes=(
            "Name-based swaps are a proxy for perceived demographic signaling, "
            "a known simplification used in audit-study literature, not a claim "
            "about the named individuals."
        ),
    )
