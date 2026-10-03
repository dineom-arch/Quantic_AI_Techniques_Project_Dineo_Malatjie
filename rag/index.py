"""FAISS index construction and deterministic persistence."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import faiss
import numpy as np

from rag.chunker import DocumentChunk
from rag.embeddings import BASELINE_MODEL
from rag.loaders import CorpusDocument


INDEX_FILENAME = "index.faiss"
CHUNKS_FILENAME = "chunks.json"
MANIFEST_FILENAME = "index_manifest.json"


class IndexValidationError(RuntimeError):
    pass


def chunk_fingerprint(chunks: list[DocumentChunk]) -> str:
    payload = "\n".join(chunk.model_dump_json() for chunk in chunks)
    return sha256(payload.encode("utf-8")).hexdigest()


def corpus_fingerprint(documents: list[CorpusDocument]) -> str:
    """Hash canonicalized authoritative inputs independently of input order."""

    canonical = [
        document.model_dump(mode="json")
        for document in sorted(documents, key=lambda item: (item.document_id, item.source_path))
    ]
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def build_faiss_index(vectors: np.ndarray) -> faiss.IndexFlatIP:
    if vectors.ndim != 2 or vectors.shape[0] == 0:
        raise IndexValidationError("Cannot build an index without embedding vectors")
    index = faiss.IndexFlatIP(int(vectors.shape[1]))
    index.add(np.ascontiguousarray(vectors, dtype="float32"))
    return index


def save_index(
    directory: Path,
    index: faiss.Index,
    chunks: list[DocumentChunk],
    *,
    model_name: str = BASELINE_MODEL,
    current_corpus_fingerprint: str,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(directory / INDEX_FILENAME))
    (directory / CHUNKS_FILENAME).write_text(
        json.dumps([chunk.model_dump(mode="json") for chunk in chunks], indent=2),
        encoding="utf-8",
    )
    manifest = {
        "format_version": 1,
        "model_name": model_name,
        "dimension": index.d,
        "chunk_count": len(chunks),
        "corpus_fingerprint": current_corpus_fingerprint,
        "chunk_fingerprint": chunk_fingerprint(chunks),
    }
    (directory / MANIFEST_FILENAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def load_index(directory: Path) -> tuple[faiss.Index, list[DocumentChunk], dict[str, object]]:
    paths = [directory / name for name in (INDEX_FILENAME, CHUNKS_FILENAME, MANIFEST_FILENAME)]
    if not all(path.is_file() for path in paths):
        raise IndexValidationError(f"RAG index artefacts are missing from {directory}")
    try:
        index = faiss.read_index(str(paths[0]))
        chunks = [DocumentChunk.model_validate(item) for item in json.loads(paths[1].read_text(encoding="utf-8"))]
        manifest = json.loads(paths[2].read_text(encoding="utf-8"))
    except Exception as exc:
        raise IndexValidationError(f"RAG index is corrupt or incompatible: {exc}") from exc
    if index.ntotal != len(chunks) or manifest.get("chunk_count") != len(chunks):
        raise IndexValidationError("RAG index and chunk metadata counts do not match")
    if manifest.get("chunk_fingerprint") != chunk_fingerprint(chunks):
        raise IndexValidationError("RAG chunk metadata fingerprint does not match")
    return index, chunks, manifest

