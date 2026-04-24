from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from readily.application.use_cases.build_inventory import InventoryMetaResponse
from readily.domain.entities import ClaimMetadata, PolicyMeta
from readily.infrastructure.llm.gemini import GeminiClient
from readily.infrastructure.llm.prompts import INGEST_POLICY_PROMPT
from readily.infrastructure.pdf.pdftotext import pages


class IngestedSection(BaseModel):
    """In-flight section returned by `ingest_policy`. Carries the verbatim
    section body so the caller can feed it to `extract_claims`. The persisted
    `PolicySection` schema type does NOT store `text` — it's consumed at
    extraction time and discarded.
    """

    heading: str
    page: int = 1
    text: str
    metadata: ClaimMetadata = Field(default_factory=ClaimMetadata)


class _IngestedPolicyResponse(BaseModel):
    meta: InventoryMetaResponse = Field(default_factory=InventoryMetaResponse)
    sections: list[IngestedSection] = Field(default_factory=list)


def ingest_policy(
    pdf_path: Path | str, client: GeminiClient
) -> tuple[PolicyMeta, list[IngestedSection]]:
    """Read a policy PDF and return doc-level metadata + body sections.

    Sections include verbatim body text (`IngestedSection.text`) so the caller
    can run claim extraction against them. The caller is responsible for
    stripping `text` when building the persisted `PolicySection`.
    """
    page_texts = pages(pdf_path)
    document = "\n\n".join(f"[page {i}]\n{t}" for i, t in enumerate(page_texts, start=1))
    prompt = INGEST_POLICY_PROMPT.format(document=document)
    response: _IngestedPolicyResponse = client.generate_structured(prompt, _IngestedPolicyResponse)

    m = response.meta
    code = (m.code or Path(pdf_path).stem.split("_", 1)[0]).strip()
    meta = PolicyMeta(
        code=code,
        file_path=str(pdf_path),
        title=(m.title or "").strip() or None,
        applicable_to=m.applicable_to,
        document_topics=m.document_topics,
        entity_refs=m.entity_refs,
    )

    sections: list[IngestedSection] = []
    for item in response.sections:
        text = item.text.strip()
        if not text:
            continue
        sections.append(
            item.model_copy(
                update={"text": text, "heading": item.heading.strip() or "(unnamed section)"}
            )
        )
    return meta, sections
