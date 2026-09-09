from occupational_fitness_rag.indexing.memory_store import InMemoryVectorStore
from occupational_fitness_rag.pipeline.austroads_rag import AustroadsRAGPipeline
from occupational_fitness_rag.retrieval.engine import RetrievalEngine
from occupational_fitness_rag.schemas.evidence_pack import RetrievalStatus
from occupational_fitness_rag.schemas.rule_result import RuleResult


def test_missing_patient_information_is_not_filled_by_rag(settings, synthetic_chunks):
    pipeline = AustroadsRAGPipeline(
        RetrievalEngine(InMemoryVectorStore(synthetic_chunks), settings.retrieval), settings
    )
    result = RuleResult(
        case_id="m",
        category="cardiovascular",
        subcondition="hypertension",
        missing=["blood_pressure_reading"],
        route="missing_information",
    )
    pack = pipeline.run(result)
    assert pack.status == RetrievalStatus.SKIPPED_MISSING_INFORMATION
    assert pack.evidence == []
