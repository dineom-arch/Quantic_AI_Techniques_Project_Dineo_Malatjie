import pytest

from rag.citations import citation_from_result
from rag.retriever import RetrievalValidationError


@pytest.mark.parametrize(
    ("query", "expected_document"),
    [
        ("PTO notice requirement", "MSG-POL-001"),
        ("active assignment PTO approval", "MSG-POL-001"),
        ("business class long haul Partner", "MSG-POL-004"),
        ("personal travel extension itinerary", "MSG-POL-003"),
        ("ordinary meal covered by per diem", "MSG-POL-006"),
        ("employee private data access", "MSG-POL-012"),
    ],
)
def test_representative_queries_retrieve_authoritative_documents(
    built_rag_service, query: str, expected_document: str
) -> None:
    results = built_rag_service.search(query, top_k=5)
    assert expected_document in {result.document_id for result in results}
    assert all(result.source_path.startswith(("policies/", "procedures/")) for result in results)


def test_k_and_document_type_filters_are_respected(built_rag_service) -> None:
    policies = built_rag_service.search("personal travel extension", top_k=3, document_type="policy")
    procedures = built_rag_service.search("personal travel extension", top_k=8, document_type="procedure")

    assert len(policies) == 3
    assert len(procedures) == 8
    assert all(result.document_type == "policy" for result in policies)
    assert all(result.document_type == "procedure" for result in procedures)


def test_invalid_search_inputs_are_rejected(built_rag_service) -> None:
    with pytest.raises(RetrievalValidationError, match="empty"):
        built_rag_service.search("   ")
    with pytest.raises(RetrievalValidationError, match="document_type"):
        built_rag_service.search("PTO", document_type="external")


def test_citation_comes_from_retrieved_metadata(built_rag_service) -> None:
    result = built_rag_service.search("PTO notice requirement", top_k=1)[0]
    citation = citation_from_result(result)

    assert citation.document_id == result.document_id
    assert citation.title == result.title
    assert citation.section == result.section
    assert citation.snippet
    assert "page" not in type(citation).model_fields
