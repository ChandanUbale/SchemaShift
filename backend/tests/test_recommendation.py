"""tests/test_recommendation.py — Stubs for scoring engine and model generator tests."""
import pytest

def test_scoring_engine_high_fk_returns_relational():
    """High FK count + frequent joins → relational → mysql."""
    raise NotImplementedError("TODO")

def test_scoring_engine_nested_returns_document():
    """Nested embedded + read-heavy → document → mongodb."""
    raise NotImplementedError("TODO")

def test_model_generator_relational_emits_ddl():
    """ModelGenerator.generate for relational returns generated_ddl with AUTO_INCREMENT."""
    raise NotImplementedError("TODO")

def test_model_generator_document_emits_tree():
    """ModelGenerator.generate for document returns model_tree dict."""
    raise NotImplementedError("TODO")

def test_ai_explainer_returns_none_when_disabled():
    """ai_explainer.explain returns None when USE_LOCAL_LLM=false."""
    raise NotImplementedError("TODO")
