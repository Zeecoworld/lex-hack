"""
Pydantic schemas shared across the API.

Core idea: a Scenario defines a prompt TEMPLATE with placeholders
(e.g. {name}, {age}, {neighborhood}) and a SwapSet for each placeholder
(a list of values grouped by demographic label). The audit engine
generates the cross-product of swaps, runs each variant through the
target LLM, and scores the outputs for disparity across groups.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OutputType(str, Enum):
    """How to interpret / score the model's response for a scenario."""
    BINARY_DECISION = "binary_decision"   # approve/deny, yes/no
    RISK_SCORE = "risk_score"             # numeric 1-10 (or similar) scale


class SwapValue(BaseModel):
    """One concrete value for a placeholder, tagged with the demographic
    group it represents (used to bucket results for scoring)."""
    value: str
    group: str  # e.g. "male", "female", "perceived_black", "perceived_white"


class SwapSet(BaseModel):
    """All candidate values for a single placeholder in the template."""
    placeholder: str          # matches "{placeholder}" in the template
    values: list[SwapValue]


class Scenario(BaseModel):
    id: str
    title: str
    description: str
    prompt_template: str      # e.g. "Should {name}, a {age}-year-old {occupation}..."
    output_type: OutputType
    swap_sets: list[SwapSet]
    # For binary_decision scoring: substrings that count as "approve"/positive
    positive_signals: list[str] = Field(default_factory=lambda: ["yes", "approve", "grant"])
    negative_signals: list[str] = Field(default_factory=lambda: ["no", "deny", "reject"])


class AuditRunRequest(BaseModel):
    scenario_id: str
    model: str = "gemini-3.8-flash"
    # Optional: cap total variants run (cross-product can get large)
    max_variants: int = 24
    # Optional: repeat each variant N times to measure output variance/noise
    repeats: int = 1


class VariantResult(BaseModel):
    variant_id: str
    filled_prompt: str
    groups: dict[str, str]     # placeholder -> group label used in this variant
    raw_outputs: list[str]     # one per repeat
    parsed_scores: list[Optional[float]]  # normalized numeric score per output (0-1 or raw scale)


class GroupDisparity(BaseModel):
    placeholder: str
    group: str
    n: int
    mean_score: float
    approval_rate: Optional[float] = None  # only meaningful for binary_decision


class AuditRunResult(BaseModel):
    run_id: str
    scenario_id: str
    model: str
    created_at: datetime
    variants: list[VariantResult]
    disparities: list[GroupDisparity]
    disparity_score: float  # headline number: max group-mean gap, per placeholder, averaged
    notes: str = ""
