from occupational_fitness_rag.retrieval.query_builder import build_filters, build_semantic_query
from occupational_fitness_rag.schemas.rule_result import RuleResult


def test_query_and_strict_filters():
    result = RuleResult(
        case_id="x",
        category="cardiovascular",
        subcondition="hypertension",
        licence_context="commercial",
        flags=["complex"],
        rules=[],
        missing=[],
        route="rag_review",
    )
    assert build_filters(result) == {
        "category": "cardiovascular",
        "subcondition": "hypertension",
        "licence_context": "commercial",
    }
    query = build_semantic_query(result)
    assert "hypertension" in query
    assert "commercial" in query
