"""CLI composition root.

Builds `Settings` once, derives all paths + client construction from it, and
passes them explicitly to each use case. No module-level path constants, no
`load_dotenv()` — `Settings` reads `.env` on its own.
"""

from __future__ import annotations

from pathlib import Path

import click

from readily.application.candidate_selector import select_candidates
from readily.application.use_cases.build_inventory import (
    build_inventory,
    load_inventory,
    policy_inventory,
    update_inventory_with_full_ingest,
)
from readily.application.use_cases.decompose_questionnaire import (
    decompose_questionnaire_batch,
)
from readily.application.use_cases.extract_claims import extract_claims
from readily.application.use_cases.ingest_policy import ingest_policy
from readily.application.use_cases.judge_question import judge_question_claim
from readily.config import Settings
from readily.domain.entities import (
    PolicyDoc,
    PolicySection,
    Question,
    QuestionClaimResult,
)
from readily.infrastructure.llm.gemini import GoogleGeminiClient
from readily.infrastructure.storage.json_store import load_list, save_list


def _flash_client(settings: Settings) -> GoogleGeminiClient:
    return GoogleGeminiClient(api_key=settings.gemini_api_key)


def _judge_client(settings: Settings) -> GoogleGeminiClient:
    return GoogleGeminiClient(
        api_key=settings.gemini_api_key,
        model="gemini-3.1-pro-preview",
        thinking_level="medium",
    )


@click.group()
@click.pass_context
def main(ctx: click.Context) -> None:
    """Readily CLI: ingest + decompose + route + judge."""
    settings = Settings()  # type: ignore[call-arg]
    settings.data_dir.mkdir(exist_ok=True)
    ctx.obj = settings


@main.command("build-inventory")
@click.pass_obj
def build_inventory_cmd(settings: Settings) -> None:
    """Populate data/inventory.json with page-1 metadata for every policy."""
    client = _flash_client(settings)
    click.echo(f"Building inventory from {settings.policy_glob!r} -> {settings.inventory_json}")
    metas = build_inventory(settings.policy_glob, client=client, cache_path=settings.inventory_json)
    with_lob = sum(1 for m in metas if m.applicable_to)
    click.echo(f"  -> {len(metas)} policies indexed; {with_lob} have applicable_to populated")


@main.command("decompose-questions")
@click.option(
    "--questionnaire",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to the questionnaire PDF (defaults to settings.questionnaire_path).",
)
@click.option("--first-page", type=int, default=None)
@click.option("--last-page", type=int, default=None)
@click.pass_obj
def decompose_questions_cmd(
    settings: Settings,
    questionnaire: Path | None,
    first_page: int | None,
    last_page: int | None,
) -> None:
    """LLM-ingest the questionnaire and extract disambiguated atomic claims."""
    source = questionnaire or settings.questionnaire_path
    client = _flash_client(settings)
    page_range = ""
    if first_page is not None or last_page is not None:
        page_range = f" (pages {first_page or 1}..{last_page or 'end'})"
    click.echo(f"Ingesting questionnaire: {source}{page_range}")
    questions = decompose_questionnaire_batch(
        source, client=client, first_page=first_page, last_page=last_page
    )
    total_claims = sum(len(q.claims) for q in questions)
    click.echo(f"  -> {len(questions)} questions, {total_claims} claims total")
    for q in questions:
        lob = ",".join(q.metadata.lob) if q.metadata.lob else "?"
        click.echo(f"  Q{q.number}: {len(q.claims)} claims  [lob={lob}]")
    save_list(settings.questions_json, questions)
    click.echo(f"Wrote {settings.questions_json}")


@main.command("route")
@click.option("--top-k", type=int, default=3)
@click.pass_obj
def route_cmd(settings: Settings, top_k: int) -> None:
    """Deterministic candidate selection — no LLM calls per question."""
    questions = load_list(settings.questions_json, Question)

    if settings.inventory_json.exists():
        inventory = load_inventory(settings.inventory_json)
        if not any(m.applicable_to or m.document_topics for m in inventory):
            click.echo(
                "Inventory cache exists but has no rich metadata; run `readily build-inventory` first."
            )
            inventory = policy_inventory(settings.policy_glob)
    else:
        click.echo(
            "No inventory cache; falling back to filename-only inventory. "
            "Run `readily build-inventory` for better narrowing."
        )
        inventory = policy_inventory(settings.policy_glob)

    if not inventory:
        click.echo(f"No policies matched {settings.policy_glob!r}; nothing to route.")
        return

    for i, q in enumerate(questions, start=1):
        codes = select_candidates(q, inventory, top_k=top_k)
        q.candidate_codes = codes
        click.echo(f"  Q{q.number} ({i}/{len(questions)}) -> {codes}")
    save_list(settings.questions_json, questions)
    click.echo(f"Updated {settings.questions_json}")


@main.command("decompose-policies")
@click.pass_obj
def decompose_policies_cmd(settings: Settings) -> None:
    """LLM-ingest each candidate policy, then extract atomic claims per section."""
    questions = load_list(settings.questions_json, Question)
    file_index = {m.code: m.file_path for m in policy_inventory(settings.policy_glob)}
    wanted_codes = sorted({c for q in questions for c in q.candidate_codes})
    click.echo(f"Decomposing {len(wanted_codes)} candidate policies")

    client = _flash_client(settings)
    policy_docs: list[PolicyDoc] = []
    for code in wanted_codes:
        file_path = file_index.get(code)
        if file_path is None:
            click.echo(f"  {code}: no file in inventory, skipping")
            continue
        click.echo(f"  {code}: ingesting {file_path} ...")
        meta, ingested = ingest_policy(file_path, client=client)
        click.echo(f"    -> {len(ingested)} sections")

        sections: list[PolicySection] = []
        total_claims = 0
        for ing in ingested:
            ctx = f"policy {meta.code} | section {ing.heading} | page {ing.page}"
            claims = extract_claims(ing.text, client=client, context=ctx, page=ing.page)
            total_claims += len(claims)
            sections.append(
                PolicySection(
                    heading=ing.heading,
                    page=ing.page,
                    metadata=ing.metadata,
                    claims=claims,
                )
            )
        policy_docs.append(PolicyDoc(meta=meta, sections=sections))
        click.echo(f"    -> {total_claims} claims")

        if settings.inventory_json.exists():
            update_inventory_with_full_ingest(settings.inventory_json, meta)

    save_list(settings.policies_json, policy_docs)
    click.echo(f"Wrote {settings.policies_json}")


@main.command("judge")
@click.pass_obj
def judge_cmd(settings: Settings) -> None:
    """Strict LLM pass: one Gemini 3 Pro call per question-claim."""
    questions = load_list(settings.questions_json, Question)
    policy_docs = load_list(settings.policies_json, PolicyDoc)
    docs_by_code = {d.meta.code: d for d in policy_docs}
    client = _judge_client(settings)

    results: list[QuestionClaimResult] = []
    total_llm_calls = 0
    for q in questions:
        if not q.claims:
            continue
        candidate_docs = [docs_by_code[c] for c in q.candidate_codes if c in docs_by_code]
        click.echo(
            f"Judging Q{q.number}: {len(q.claims)} claims x {len(candidate_docs)} candidate docs"
        )
        for qc_idx, qc in enumerate(q.claims, start=1):
            best, contradictions = judge_question_claim(qc, candidate_docs, client=client)
            total_llm_calls += 1
            verdict_str = (
                f"MATCH {best.policy_code} §{best.section} conf={best.confidence:.0f}"
                if best is not None
                else "no match"
            )
            contra_str = f", {len(contradictions)} contradictions" if contradictions else ""
            click.echo(f"  qc{qc_idx}: {verdict_str}{contra_str}")
            results.append(
                QuestionClaimResult(
                    question_number=q.number,
                    question_claim=qc,
                    best_match=best,
                    contradictions=contradictions,
                )
            )
    save_list(settings.results_json, results)
    click.echo(
        f"Wrote {settings.results_json} ({len(results)} claim-results, {total_llm_calls} LLM calls)"
    )


@main.command("run")
@click.option("--questionnaire", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--top-k", type=int, default=3)
@click.pass_context
def run_cmd(ctx: click.Context, questionnaire: Path | None, top_k: int) -> None:
    """Run the full pipeline end-to-end."""
    settings: Settings = ctx.obj
    if not settings.inventory_json.exists():
        ctx.invoke(build_inventory_cmd)
    ctx.invoke(decompose_questions_cmd, questionnaire=questionnaire)
    ctx.invoke(route_cmd, top_k=top_k)
    ctx.invoke(decompose_policies_cmd)
    ctx.invoke(judge_cmd)


if __name__ == "__main__":  # pragma: no cover
    main()
