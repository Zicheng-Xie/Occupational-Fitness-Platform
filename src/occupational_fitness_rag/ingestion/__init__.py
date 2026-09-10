from .models import GuidelineChunk, ParsedBlock

__all__ = ["ParsedBlock", "GuidelineChunk", "ingest_pdf_to_chunks"]


def __getattr__(name: str):
    """Keep lightweight models usable when optional PDF support is not imported."""
    if name == "ingest_pdf_to_chunks":
        from .pipeline import ingest_pdf_to_chunks

        return ingest_pdf_to_chunks
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
