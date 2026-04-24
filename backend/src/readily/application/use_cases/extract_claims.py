from __future__ import annotations

from pydantic import BaseModel, Field

from readily.domain.entities import Claim, ClaimMetadata
from readily.infrastructure.llm.gemini import GeminiClient
from readily.infrastructure.llm.prompts import DISAMBIGUATE_PROMPT, EXTRACT_STATEMENTS_PROMPT

class ExtractedStatement(BaseModel):
    claim: str
    source_text: str
    metadata: ClaimMetadata = Field(default_factory=ClaimMetadata)


class ExtractStatementsResponse(BaseModel):
    statements: list[ExtractedStatement] = Field(default_factory=list)


class DisambiguateResponse(BaseModel):
    disambiguated: str


def extract_claims(
    text: str,
    client: GeminiClient,
    *,
    context: str = "",
    page: int | None = None,
) -> list[Claim]:
    """Extract atomic claims from a policy section.

    Two LLM calls per unit: one to enumerate statements with metadata, then
    one per statement to rewrite it standalone. Statements that cannot be
    disambiguated are dropped.
    """
    unit = text.strip()
    if not unit:
        return []
    response = _extract_statements(unit, context=context, client=client)
    claims: list[Claim] = []
    for s in response.statements:
        raw = s.claim.strip()
        quote = s.source_text.strip()
        if not raw:
            continue
        disambig = _disambiguate_statement(
            statement=raw, source_unit=unit, context=context, client=client
        )
        if disambig is None:
            continue
        claims.append(
            Claim(
                claim=disambig,
                source_text=quote,
                page=page,
                metadata=s.metadata,
            )
        )
    return claims


def _extract_statements(
    unit: str, *, context: str, client: GeminiClient
) -> ExtractStatementsResponse:
    prompt = EXTRACT_STATEMENTS_PROMPT.format(context=context or "(none)", unit=unit)
    result: ExtractStatementsResponse = client.generate_structured(
        prompt, ExtractStatementsResponse
    )
    return result


def _disambiguate_statement(
    *, statement: str, source_unit: str, context: str, client: GeminiClient
) -> str | None:
    prompt = DISAMBIGUATE_PROMPT.format(
        context=context or "(none)",
        source_unit=source_unit,
        statement=statement,
    )
    response: DisambiguateResponse = client.generate_structured(prompt, DisambiguateResponse)
    return response.disambiguated.strip() or None
