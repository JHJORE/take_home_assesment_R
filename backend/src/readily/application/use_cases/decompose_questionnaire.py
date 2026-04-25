"""Two-call questionnaire decomposition.

Call 1 ingests the questionnaire PDF and emits every question with its atomic
statements and question-level metadata in a single structured response. Call 2
takes the same source document plus all extracted statements and returns
disambiguated text for each. Total cost is fixed at two LLM calls regardless of
how many questions or statements the questionnaire contains.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from readily.domain.entities import Claim, ClaimMetadata, Question, QuestionMetadata
from readily.infrastructure.llm.gemini import GeminiClient
from readily.infrastructure.llm.prompts import (
    BATCH_DISAMBIGUATE_PROMPT,
    INGEST_AND_EXTRACT_PROMPT,
)
from readily.infrastructure.pdf.pdftotext import pages


class _BatchStatement(BaseModel):
    claim: str
    source_text: str
    metadata: ClaimMetadata = Field(default_factory=ClaimMetadata)


class _BatchQuestion(BaseModel):
    number: int
    text: str
    reference: str = ""
    page: int | None = None
    metadata: QuestionMetadata = Field(default_factory=QuestionMetadata)
    statements: list[_BatchStatement] = Field(default_factory=list)


class _BatchDisambItem(BaseModel):
    question_number: int
    statement_index: int
    disambiguated: str


class _BatchDisambResponse(BaseModel):
    items: list[_BatchDisambItem]


def decompose_questionnaire_batch(
    pdf_path: Path | str,
    client: GeminiClient,
    *,
    first_page: int | None = None,
    last_page: int | None = None,
) -> list[Question]:
    """Two Gemini calls: (1) ingest+extract, (2) batch disambiguate.

    Call 1 emits every question with its atomic statements and question-level
    metadata in one shot. Call 2 takes the full source document plus all
    statements and returns disambiguated text for each.
    """
    base_page = first_page or 1
    page_texts = pages(pdf_path, first_page=first_page, last_page=last_page)
    document = "\n\n".join(f"[page {base_page + i}]\n{t}" for i, t in enumerate(page_texts))

    prompt1 = INGEST_AND_EXTRACT_PROMPT.format(document=document)
    batch_questions: list[_BatchQuestion] = client.generate_structured(
        prompt1, list[_BatchQuestion]
    )

    disamb_input = [
        {
            "number": bq.number,
            "text": bq.text,
            "reference": bq.reference,
            "statements": [
                {"index": i, "claim": s.claim, "source_text": s.source_text}
                for i, s in enumerate(bq.statements)
            ],
        }
        for bq in batch_questions
    ]
    prompt2 = BATCH_DISAMBIGUATE_PROMPT.format(
        document=document, questions_json=json.dumps(disamb_input, indent=2)
    )
    disamb: _BatchDisambResponse = client.generate_structured(prompt2, _BatchDisambResponse)
    disamb_map = {(it.question_number, it.statement_index): it.disambiguated for it in disamb.items}

    questions: list[Question] = []
    for bq in batch_questions:
        claims: list[Claim] = []
        for idx, s in enumerate(bq.statements):
            disamb_text = disamb_map.get((bq.number, idx)) or s.claim
            claims.append(
                Claim(
                    claim=disamb_text,
                    source_text=s.source_text,
                    page=bq.page,
                    metadata=s.metadata,
                )
            )
        questions.append(
            Question(
                number=bq.number,
                text=bq.text,
                reference=bq.reference,
                metadata=bq.metadata,
                claims=claims,
            )
        )
    return questions
