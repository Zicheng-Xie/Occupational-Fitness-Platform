from occupational_fitness_rag.indexing.memory_store import InMemoryVectorStore
from occupational_fitness_rag.pipeline.austroads_rag import AustroadsRAGPipeline
from occupational_fitness_rag.retrieval.engine import RetrievalEngine
from occupational_fitness_rag.schemas.evidence_pack import RetrievalStatus
from occupational_fitness_rag.schemas.rule_result import RuleResult


def _pipeline(settings, chunks):
    return AustroadsRAGPipeline(
        RetrievalEngine(InMemoryVectorStore(chunks), settings.retrieval), settings
    )


def test_fast_path_bypasses_rag(settings, synthetic_chunks):
    result = RuleResult(
        case_id="f", category="vision", subcondition="visual_acuity", route="fast_path"
    )
    pack = _pipeline(settings, synthetic_chunks).run(result)
    assert pack.status == RetrievalStatus.SKIPPED_FAST_PATH
    assert pack.evidence == []


def test_rag_review_runs(settings, synthetic_chunks):
    result = RuleResult(
        case_id="r",
        category="cardiovascular",
        subcondition="hypertension",
        flags=["complex"],
        route="rag_review",
    )
    pack = _pipeline(settings, synthetic_chunks).run(result)
    assert pack.status == RetrievalStatus.FOUND
    assert pack.evidence
