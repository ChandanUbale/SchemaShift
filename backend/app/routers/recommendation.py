"""routers/recommendation.py — Relational-vs-document scoring and model generation."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.recommendation import RecommendationRequest, RecommendationResult

router = APIRouter()


@router.post("/", response_model=RecommendationResult)
def get_recommendation(payload: RecommendationRequest, db: Session = Depends(get_db)):
    """
    Run the deterministic rule engine to score relational vs document.
    Returns target_type (mysql | mongodb), confidence %, and rule-based reasons.

    Optionally calls Ollama to rewrite reasons as prose (only if USE_LOCAL_LLM=true).
    Falls back to template reasons if Ollama is unavailable — never blocks.

    TODO:
    - Load profiling results from DB for connection_id
    - scoring_engine.score(profiling_result, workload_form)
    - model_generator.generate(recommendation)
    - Optionally: ai_explainer.explain(recommendation)
    """
    raise NotImplementedError("TODO: implement get_recommendation")


@router.get("/{plan_id}", response_model=RecommendationResult)
def get_plan(plan_id: str, db: Session = Depends(get_db)):
    """Return a previously generated recommendation + model plan."""
    raise NotImplementedError("TODO: implement get_plan")
