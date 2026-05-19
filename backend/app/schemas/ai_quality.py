"""Block F V2.0 F5b — pydantic schemas for AI feedback + admin AI quality.

Owned by ``api/v1/ai_feedback.py`` and ``api/v1/admin_ai.py``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

FeedbackCategory = Literal[
    "grammar",
    "unnatural",
    "factual",
    "too_long",
    "too_short",
    "other",
]


class AIFeedbackCreate(BaseModel):
    """Seller-submitted feedback row — input to ``POST /ai-feedback``."""

    generation_id: Optional[UUID] = None
    listing_id: UUID
    category: FeedbackCategory
    comment: Optional[str] = Field(default=None, max_length=2000)


class AIFeedbackResponse(BaseModel):
    """Single feedback row, used for both seller-create response and the
    admin feedback queue."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    generation_id: Optional[UUID]
    listing_id: Optional[UUID]
    user_id: UUID
    category: str
    comment: Optional[str]
    handled: bool
    created_at: datetime


class AIFeedbackList(BaseModel):
    total: int
    page: int
    items: list[AIFeedbackResponse]


# ────────────────────────────────────────────────────────────
# Admin: generations
# ────────────────────────────────────────────────────────────


class AIGenerationSummary(BaseModel):
    """Row in ``GET /admin/ai/generations`` (no full prompt/response —
    those land in the detail endpoint to keep list payloads small)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    listing_id: Optional[UUID]
    prompt_template_id: Optional[UUID]
    model: str
    duration_ms: int
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    cost_usd_micros: Optional[int]
    triggered_by: str
    outcome: str
    created_at: datetime


class AIGenerationDetail(AIGenerationSummary):
    """Full row including LLM input/output text. Admin-only."""

    prompt_text: str
    response_text: str


class AIGenerationList(BaseModel):
    total: int
    page: int
    items: list[AIGenerationSummary]


# ────────────────────────────────────────────────────────────
# Admin: prompts
# ────────────────────────────────────────────────────────────


class PromptTemplateResponse(BaseModel):
    # ``model_hint`` collides with pydantic's protected ``model_`` namespace
    # — explicitly clear ``protected_namespaces`` so the field name (which
    # mirrors the DB column) stays as-is.
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    kind: str
    version: int
    body: str
    model_hint: Optional[str]
    is_active: bool
    notes: Optional[str]
    created_by_user_id: Optional[UUID]
    created_at: datetime


class PromptTemplateCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    kind: str = Field(..., min_length=1, max_length=48)
    body: str = Field(..., min_length=1)
    model_hint: Optional[str] = Field(default=None, max_length=64)
    notes: Optional[str] = Field(default=None, max_length=2000)


# ────────────────────────────────────────────────────────────
# Admin: metrics overview (used by /admin/ai/metrics)
# ────────────────────────────────────────────────────────────


class AIMetricsSnapshot(BaseModel):
    """Aggregated quality metrics over the last 24h window."""

    window_hours: int
    total_generations: int
    ok_count: int
    fallback_count: int
    failure_count: int
    bad_feedback_count: int
    bad_feedback_rate: float
    duration_p50_ms: Optional[int]
    duration_p95_ms: Optional[int]
    cost_usd_today: float
    alert_states: dict[str, bool]  # metric → currently-tripped?
