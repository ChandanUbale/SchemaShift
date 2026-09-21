"""tests/test_recommendation.py — Stubs for scoring engine and model generator tests."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_scoring_engine_high_fk_returns_relational():
    """High FK count + frequent joins → relational → mysql."""
    pytest.skip("Chandan scoring engine — out of scope for this branch")


def test_scoring_engine_nested_returns_document():
    """Nested embedded + read-heavy → document → mongodb."""
    pytest.skip("Chandan scoring engine — out of scope for this branch")


def test_model_generator_relational_emits_ddl():
    """ModelGenerator.generate for relational returns generated_ddl with AUTO_INCREMENT."""
    pytest.skip("Chandan model generator — out of scope for this branch")


def test_model_generator_document_emits_tree():
    """ModelGenerator.generate for document returns model_tree dict."""
    pytest.skip("Chandan model generator — out of scope for this branch")


def test_ai_explainer_returns_none_when_disabled():
    """ai_explainer.explain returns None when USE_LOCAL_LLM=false."""
    import asyncio
    from app.config import settings
    from app.services.recommendation.ai_explainer import explain

    assert settings.use_local_llm is False
    result = asyncio.run(explain({"target_type": "mysql", "reasons": [{"message": "high fk"}]}))
    assert result is None
