"""Prompts for the Readily pipeline.

Every metadata-producing prompt embeds the DOMAIN_CONTEXT block so the LLM emits
highest-quality structured metadata (not most metadata). The block spells out:
  - which health plan this is and what the four LOBs mean
  - what each two-letter policy code prefix maps to
  - the CalOptima P&P template structure (header fields, PURPOSE, Roman/letter sections)
  - APL and reference conventions
  - formally defined terms (capitalized) vs everyday vocabulary
  - a negative-keyword list (generic filler to never emit)
  - keyword-quality heuristics (multi-word noun phrases, synonym pairs for drift)

Same symmetric metadata schema on question-side and policy-side so the
candidate_selector can match by deterministic set-overlap with no further LLM calls.
"""

DOMAIN_CONTEXT = """DOMAIN CONTEXT — CalOptima Health Policies & Procedures
=========================================================

You are working with Policies and Procedures (P&Ps) from CalOptima Health, an Orange
County public health plan. Use this context to produce high-quality, consistent,
domain-aware metadata.

LINES OF BUSINESS (LOBs). Every policy applies to one or more of these four:
  - "Medi-Cal" — California's Medicaid program (largest LOB)
  - "OneCare" — CalOptima's Medicare Advantage D-SNP plan
  - "PACE" — Program of All-Inclusive Care for the Elderly
  - "Administrative" — internal / governance (not member-facing)
LOB is encoded on page 1 as a checkbox list. "☒" (crossed box) = applicable; "☐" (empty
box) = not applicable. A policy may apply to multiple LOBs.

POLICY CODE PREFIXES. The first two letters of a policy code identify its domain.
Use this mapping — do not guess from the filename:
  - AA  = Administrative / governance (glossaries, gifts, advisory committees,
          auto-assignment methodology, public records, grants, DHCS submission process)
  - DD  = Member Services (rights, enrollment, orientation, informing materials,
          PCP selection, customer-service grievance, cultural and linguistic)
  - EE  = Provider Network Management (directory, credentialing, training, contracts,
          MOUs, encounter reporting)
  - FF  = Medi-Cal Financial (capitation, fee schedule, claims processing,
          reinsurance, risk pools)
  - GA  = Operations / facilities (service animals, mail, street medicine,
          smoking restrictions — a small grab-bag)
  - GG  = Medical Management — the large clinical bucket (hospice, palliative,
          utilization management, prior authorization, specialty care, mental health,
          transplants, SNF/LTC, pharmacy clinical rules)
  - HH  = Compliance / Grievances / Fraud, Waste & Abuse / Sanctions /
          Protected Health Information / delegated-entity oversight
  - MA  = OneCare / Medicare Advantage LOB (marketing, brokers, Part D, LIS)
  - PA  = PACE LOB (Program of All-Inclusive Care for the Elderly — this is a LOB
          code, NOT Pharmacy/Prior Authorization)
  - CMC = OneCare Connect legacy dual-eligible (only 4 policies:
          capitation, grievance, standard appeal, payment appeal)

POLICY TEMPLATE STRUCTURE. CalOptima P&Ps follow a consistent format:
  Page 1 header block:
    Policy:          <code e.g. GG.1503>
    Title:           <title>
    Department:      <owning department>
    Section:         <sub-team within department>
    CEO Approval:    /s/ <name> <MM/DD/YYYY>
    Effective Date:  <MM/DD/YYYY>
    Revised Date:    <MM/DD/YYYY>
    Applicable to:   ☒/☐ Medi-Cal  ☒/☐ OneCare  ☒/☐ PACE  ☒/☐ Administrative
  Page 1 body starts with "I. PURPOSE" — one paragraph describing scope.
  Main body: "I." "II." "III." Roman sections, each containing "A." "B." "C."
  letter subsections. Final sections typically cover REFERENCES and ATTACHMENTS.

APL AND REFERENCE CONVENTIONS.
  - "APL YY-NNN" = All Plan Letter from DHCS (e.g. APL 25-008).
    Unless the text says otherwise, APL 25-xxx applies to Medi-Cal Managed Care.
    APL references are a strong LOB anchor — capture them in entity_refs.
  - Other citation patterns to capture in entity_refs:
    "Medicare Benefit Policy Manual, Chapter N section N.N", "W&I §N",
    "Welfare & Institutions Code §N", "42 CFR §N.N", "Title XIX", DHCS contract sections.

DEFINED / PROPER TERMS. These are formally defined in the CalOptima glossary (AA.1000).
When they appear capitalized, they are the defined term; copy them verbatim into
entity_refs where relevant:
  Member, Provider, Plan, MCP, Health Network, CHCN (CalOptima Health Community
  Network), DHCS, Managed Care Plan, Authorized Representative, Medical Necessity /
  Medically Necessary, Prior Authorization, Benefit Period, Election Statement,
  Terminal Illness, Single Case Agreement, Letter of Agreement, Fraud Waste and Abuse.

NEGATIVE-KEYWORD LIST. Never emit these as topic_keywords — they are domain-ubiquitous
filler and make matching noisy:
  service, services, member, members, plan, plans, policy, procedure, p&p, mcp, mcps,
  requirement, requirements, must, shall, should, may, will, have, provide, ensure,
  process, processes, state, states, include, includes

KEYWORD-QUALITY HEURISTICS:
  - Prefer multi-word noun phrases over single generic words.
    GOOD: "benefit period", "single case agreement", "prior authorization",
          "election statement", "hospice Provider", "face-to-face encounter".
    BAD: "period", "agreement", "authorization", "election", "provider".
  - If a policy's title contains a term, that term is a high-signal topic keyword.
  - If regulator text and plan text use different words for the same concept
    ("retrospective request" vs "post-service review"; "election statement"
    vs "hospice election"), emit BOTH so matching handles terminology drift.
  - Use lowercase for topic_keywords unless the term is a capitalized proper noun
    (in which case it belongs in entity_refs, not topic_keywords).
=========================================================
"""


INVENTORY_POLICY_PROMPT = (
    DOMAIN_CONTEXT
    + """

TASK — POLICY INVENTORY (page 1 only).

You will be given the text of **page 1** of a CalOptima P&P. Extract the header
block and produce document-level routing metadata. This is a cheap one-pass
extraction used to populate a cached inventory; it is NOT the full ingestion.

What to extract:
  - "code": the policy identifier from "Policy:" (e.g. "GG.1503", "AA.1207a"). Copy verbatim.
  - "title": the policy title from "Title:". Collapse line wraps — "Auto-\\nAssignment" -> "Auto-Assignment".
  - "applicable_to": list of LOBs marked with "☒" (crossed box). Omit those marked "☐".
                     Values must be drawn from: "Medi-Cal", "OneCare", "PACE", "Administrative".
  - "document_topics": 5-12 salient topic terms describing what this policy covers,
                        derived from the title AND the "I. PURPOSE" paragraph AND the
                        first section heading if present. Apply the NEGATIVE-KEYWORD
                        LIST and KEYWORD-QUALITY HEURISTICS from the domain context —
                        prefer multi-word noun phrases. Use the code prefix as a sanity
                        check (PA.xxxx -> PACE-related topics; HH.xxxx -> compliance topics).
  - "entity_refs": proper nouns, APL citations, statute citations, and defined terms
                    that appear on page 1. Copy verbatim.

Return a JSON object with this exact shape:
  {{"code": "...", "title": "...",
    "applicable_to": ["Medi-Cal"],
    "document_topics": ["..."],
    "entity_refs": ["..."]}}

Return ONLY the JSON object. No prose, no code fences.

PAGE 1 TEXT:
\"\"\"
{page_text}
\"\"\""""
)


INGEST_POLICY_PROMPT = (
    DOMAIN_CONTEXT
    + """

TASK — FULL POLICY INGESTION.

You will be given the full text of a CalOptima P&P. Page boundaries are marked
inline as "[page N]". Your task is to return:
  1. The document-level metadata block (richer than the inventory seed — consolidate
     document_topics across all sections, not just page 1).
  2. The body, split into the document's own logical sections.
  3. Per-section claims with claim-level metadata, ready for downstream matching.

META FIELDS (all optional — include only what the document actually states):
  - code, title: as in the inventory prompt.
  - applicable_to: list of LOBs marked "☒" on page 1.
  - document_topics: 8-20 terms covering ALL the sub-topics this document addresses
    across its whole body (not just page 1). Apply the negative-keyword list and
    keyword-quality heuristics. Multi-word noun phrases preferred.
  - entity_refs: proper nouns, APL/statute citations, defined terms cited anywhere
    in the document.

SECTIONS. Split the document as its own structure presents it (Roman "I.", "II.",
letters "A.", "B.", numbered paragraphs, or plain-prose headings — whatever is
actually there). For each section emit:
  - "heading": the section heading as it appears in the document ("II.A Hospice
               Coverage", "B. Eligibility", etc.). If a block has no heading,
               synthesize a short phrase (5-10 words).
  - "page":    1-indexed page the section starts on (from the [page N] markers).
  - "text":    verbatim body text. Do NOT paraphrase, reorder, or summarize. Include
               the heading at the start. Strip the [page N] markers from the text.
  - "metadata": claim-level-style metadata summarizing this SECTION (not individual
                claims yet — claims are extracted in a later stage). Shape:
                {{"topic_keywords": [...], "entity_refs": [...]}}.
                Apply the same negative-keyword list and heuristics.

RULES:
  - Preserve numeric values, dates, percentages, defined terms, and proper nouns verbatim.
  - "text" must be a verbatim substring of the document (minus [page N] markers).
  - Skip pure boilerplate: page headers/footers, signature blocks, revision logs,
    cover-page labels already captured in meta.
  - If the document has no recognizable body sections (e.g. one-page attestation),
    emit one section containing the whole body.

Return a JSON object with this exact shape:
  {{"meta": {{"code": "...", "title": "...",
             "applicable_to": ["..."],
             "document_topics": ["..."], "entity_refs": ["..."]}},
    "sections": [{{"heading": "...", "page": <int>, "text": "...",
                   "metadata": {{"topic_keywords": ["..."], "entity_refs": ["..."]}}}}]}}

Return ONLY the JSON object. No prose, no code fences.

DOCUMENT:
\"\"\"
{document}
\"\"\""""
)


EXTRACT_STATEMENTS_PROMPT = (
    DOMAIN_CONTEXT
    + """

TASK — EXTRACT ATOMIC STATEMENTS WITH METADATA.

You will be given one UNIT of text. It may be:
  - a regulatory questionnaire question (often phrased as yes/no:
    "Does the P&P state that..."),
  - a section of a CalOptima policy or procedure document.

Your task:
  1. Emit every specific, verifiable factual proposition that the unit encodes,
     as a list of atomic declarative statements.
  2. For each statement, attach metadata that mirrors the schema on the other side,
     so downstream matching can compare question-claims against policy-claims with a
     deterministic set-overlap score (no LLM).
  3. If the UNIT is a question (the CONTEXT names an APL reference, or the text
     begins with "Does the P&P ..."), also emit a question-level metadata block
     describing the WHOLE question. Omit this block for policy sections.

A STATEMENT is:
  - atomic: one obligation, definition, rate, deadline, eligibility rule, or
    requirement per statement. "MCPs must do X and Y" -> two statements.
  - declarative: always a fact, never a question. Flip "Does the P&P state that X?"
    to "X". The wrapper "the P&P states that" is NOT part of the proposition.
  - faithful: never invent facts, never infer beyond the unit, never import outside knowledge.
  - verifiable: concrete enough that a fact-checker could point to a sentence in
    a policy and say yes/no.

PER-STATEMENT METADATA (apply the domain-context rules — negative-keyword list,
multi-word noun phrases, defined terms go to entity_refs):
  - "topic_keywords": 3-8 salient noun phrases specific to THIS statement.
  - "entity_refs": proper nouns, APL/statute citations, and defined terms the
    statement cites (copy verbatim, preserve capitalization).

QUESTION-LEVEL METADATA (only when the UNIT is a question — emit once for the
whole call):
  - "lob": derived from the reference (APL 25-xxx -> ["Medi-Cal"] unless the text
           says otherwise; OneCare/MA references -> ["OneCare"]; PACE -> ["PACE"]).
  - "reference": the APL or other citation from the CONTEXT or question text
                 (e.g. "APL 25-008"). Empty string if none.
  - "question_topics": 3-8 noun phrases describing what the WHOLE question is
                        about (broader than any one statement's topic_keywords).

RULES:
  - Preserve numeric values, dates, percentages, defined terms, and proper nouns verbatim.
  - If the unit lists items by reference only ("the 12 listed services"), emit ONE
    statement capturing the reference; do NOT fabricate the list.
  - If the unit enumerates items inline (a bulleted or comma-separated list),
    emit one statement per item OR one statement capturing the set, whichever
    better preserves the source's granularity.
  - Drop pure headers, PURPOSE blurbs, section labels, "See Attachment X" meta-text.
  - Drop sentences whose ambiguity cannot be resolved from the unit itself.

Each statement must carry a verbatim "source_text" — a substring of the UNIT that
the statement is derived from. Same casing, same punctuation.

Return a JSON OBJECT with this exact shape. For policy sections the "question"
field is omitted or null.

  {{
    "statements": [
      {{"claim": "<atomic declarative statement>",
        "source_text": "<verbatim substring of the UNIT>",
        "metadata": {{"topic_keywords": ["..."],
                      "entity_refs": ["..."]}}}}
    ]
  }}

Return ONLY the JSON object. No prose, no code fences, no commentary.

CONTEXT: {context}

UNIT:
\"\"\"
{unit}
\"\"\""""
)


DISAMBIGUATE_PROMPT = """You rewrite a single atomic statement so it stands alone without its source.

You will be given:
  - a SOURCE_UNIT (the full regulatory question or policy section the statement was extracted from),
  - a STATEMENT (one atomic declarative proposition already extracted from that unit),
  - optional CONTEXT (e.g. "policy GG.1234 | section II.A | page 3" or "Reference: APL 25-008, page 1").

Your task is to return a version of STATEMENT that is fully self-contained: a reader with no access to the SOURCE_UNIT or CONTEXT should be able to understand it correctly.

Resolve these kinds of ambiguity, using only the SOURCE_UNIT and the CONTEXT:
  - referential ambiguity: pronouns ("it", "they", "them"), demonstratives ("this", "these", "such"), and bare references ("the plan", "the program", "the contractor", "the member", "the policy") whose referent is identified by the SOURCE_UNIT.
  - partial names and undefined acronyms: if SOURCE_UNIT or CONTEXT gives the full name or definition, use it.
  - structural ambiguity: if coordination scope ("A and B within 14 days") is unclear but SOURCE_UNIT disambiguates it, make the scope explicit.

Rules:
  - Resolve ambiguity ONLY from the SOURCE_UNIT and the CONTEXT. Never import outside knowledge.
  - Preserve numeric values, dates, percentages, defined terms, and proper nouns verbatim.
  - If STATEMENT is already self-contained, return it unchanged in the "disambiguated" field.
  - Do NOT invent list items, dates, or thresholds that are not in the SOURCE_UNIT.

Return a JSON object with this exact shape:
  {{"disambiguated": "<standalone version of STATEMENT>"}}

Return ONLY the JSON object. No prose, no code fences.

CONTEXT: {context}

SOURCE_UNIT:
\"\"\"
{source_unit}
\"\"\"

STATEMENT:
\"\"\"
{statement}
\"\"\""""


INGEST_AND_EXTRACT_PROMPT = (
    DOMAIN_CONTEXT
    + """

TASK — INGEST QUESTIONS AND EXTRACT ATOMIC STATEMENTS IN ONE PASS.

You will be given the full text of a regulatory questionnaire PDF (or an excerpt
of one). Page boundaries are marked inline as "[page N]". In a SINGLE pass,
identify every regulatory question and, for each question, emit its atomic
declarative statements with metadata AND a question-level metadata block. No
separate ingestion step — one JSON array covers everything.

What counts as a question:
  - A numbered or lettered item asking whether the organization's policies and
    procedures (P&P) state, cover, or meet a requirement.
  - May be phrased as yes/no ("Does the P&P state that...") or as a statement
    the P&P must match ("The P&P shall state that...").
  - May include embedded sub-parts, list references, or continuation text.

What to SKIP:
  - Form instructions, headers, footers, signature blocks, revision histories,
    table-of-contents entries.
  - Narrative preamble/background that is not itself a question.
  - Numbered section headings that introduce questions but are not questions themselves.

For each question, emit:
  - "number": integer identifier. If the document uses non-integer identifiers
    (e.g. "Q1", "A.1", "1.a"), normalize to a sequential integer in document order
    starting at 1.
  - "text": full question text, verbatim (no leading number).
  - "reference": parenthetical provenance metadata (e.g. "(Reference: APL 25-008, page 1)").
    "" if absent.
  - "page": 1-indexed absolute page the question STARTS on, read from the nearest
    preceding "[page N]" marker. These markers give the document's true page
    numbers, so copy them verbatim — do NOT renumber from 1.
  - "metadata": QUESTION-LEVEL block describing the WHOLE question:
      - "lob": LOB list derived from the reference (APL 25-xxx -> ["Medi-Cal"]
               unless the text says otherwise; OneCare/MA -> ["OneCare"]; PACE -> ["PACE"]).
      - "reference": the bare APL or other citation (e.g. "APL 25-008"). "" if none.
      - "question_topics": 3-8 noun phrases describing what the whole question is
                            about (broader than any one statement's topic_keywords).
  - "statements": list of atomic declarative statements. Each statement object has:
      - "claim": atomic, declarative, faithful, verifiable proposition. Flip
                 "Does the P&P state that X?" to "X". The wrapper "the P&P states
                 that" is NOT part of the proposition.
      - "source_text": verbatim substring of the QUESTION text the statement is
                       derived from. Same casing, same punctuation.
      - "metadata":
          - "topic_keywords": 3-8 salient noun phrases specific to THIS statement.
          - "entity_refs": proper nouns, APL/statute citations, defined terms —
            copy verbatim, preserve capitalization.

STATEMENT rules (apply per statement):
  - Atomic: one obligation, definition, rate, deadline, eligibility rule, or
    requirement per statement. "MCPs must do X and Y" -> two statements.
  - Declarative: always a fact, never a question.
  - Faithful: never invent facts, never infer beyond the unit, never import outside knowledge.
  - Verifiable: concrete enough that a fact-checker could point to a sentence in
    a policy and say yes/no.
  - If the question lists items by reference only ("the 12 listed services"),
    emit ONE statement capturing the reference; do NOT fabricate the list.
  - If the question enumerates items inline (bulleted or comma-separated),
    emit one statement per item OR one statement capturing the set, whichever
    better preserves the source's granularity.
  - Drop headers, PURPOSE blurbs, "See Attachment X" meta-text.

METADATA rules — apply the negative-keyword list, multi-word noun phrase
preference, and defined-terms-to-entity_refs routing from the domain context.

Return a JSON array with one object per question, exactly this shape:

  [
    {{
      "number": <int>,
      "text": "<full question text>",
      "reference": "<provenance or empty string>",
      "page": <int>,
      "metadata": {{
        "lob": ["Medi-Cal"],
        "reference": "APL 25-008",
        "question_topics": ["..."]
      }},
      "statements": [
        {{
          "claim": "<atomic declarative statement>",
          "source_text": "<verbatim substring of the question>",
          "metadata": {{
            "topic_keywords": ["..."],
            "entity_refs": ["..."]
          }}
        }}
      ]
    }}
  ]

Return ONLY the JSON array. No prose, no code fences, no commentary.

DOCUMENT:
\"\"\"
{document}
\"\"\""""
)


BATCH_DISAMBIGUATE_PROMPT = """You disambiguate a batch of atomic statements so each stands alone without its source.

You will be given:
  - SOURCE_DOCUMENT: the full text of the questionnaire excerpt the statements were extracted from.
  - QUESTIONS: a JSON array of questions, each with its extracted statements (indexed).

For EVERY statement in every question, return a disambiguated version of the statement text
that is fully self-contained: a reader with no access to SOURCE_DOCUMENT or the parent question
should understand it correctly.

Resolve these kinds of ambiguity, using ONLY the SOURCE_DOCUMENT and the parent question context:
  - referential ambiguity: pronouns ("it", "they", "them"), demonstratives ("this", "these",
    "such"), and bare references ("the plan", "the program", "the contractor", "the member",
    "the policy") whose referent is identified by the SOURCE_DOCUMENT or the parent question.
  - partial names and undefined acronyms: if the SOURCE_DOCUMENT or the parent question gives
    the full name or definition, use it.
  - structural ambiguity: if coordination scope ("A and B within 14 days") is unclear but the
    source disambiguates it, make the scope explicit.

Rules:
  - Resolve ambiguity ONLY from SOURCE_DOCUMENT and the parent question context. Never import outside knowledge.
  - Preserve numeric values, dates, percentages, defined terms, and proper nouns verbatim.
  - If STATEMENT is already self-contained, return it unchanged.
  - Do NOT invent list items, dates, or thresholds that are not in the SOURCE_DOCUMENT.

Return a JSON object with this exact shape, one entry per (question_number, statement_index) pair:
  {{
    "items": [
      {{"question_number": <int>, "statement_index": <int>, "disambiguated": "<standalone text>"}}
    ]
  }}

Return ONLY the JSON object. No prose, no code fences.

SOURCE_DOCUMENT:
\"\"\"
{document}
\"\"\"

QUESTIONS:
{questions_json}
"""


JUDGE_PROMPT = """You are a strict compliance analyst deciding whether any of these candidate policy statements cover (or contradict) a regulator's requirement.

The REGULATOR'S CLAIM (what the questionnaire asks us to prove the P&P covers):
  "{q_claim}"

CANDIDATE POLICY CLAIMS (every claim from the candidate policy documents; each line names its policy, section, and page so you can reason about provenance):
{candidates_rendered}

Be strict. Most candidates will be UNRELATED — that's expected. Only emit MATCH when the policy claim really would satisfy a regulator citing this requirement. When multiple candidates plausibly MATCH, assign confidence honestly so the best one wins by numeric ranking.

For each candidate, output a verdict:
  - "MATCH"         : this policy claim entails or paraphrases the regulator's claim, even under terminology drift (e.g. "retrospective request" ↔ "post-service review"). A regulator would accept this as a compliant citation.
  - "CONTRADICTION" : this policy claim cannot both be true with the regulator's claim. They conflict on obligation, threshold, scope, or numeric quantity.
  - "UNRELATED"     : neither of the above. Use this liberally — being strict is the point.

For MATCH and CONTRADICTION verdicts, also emit a `confidence` integer from 0-100 calibrated as follows:
  - 90-100 : near-verbatim paraphrase; same terminology; same numeric values where relevant — a regulator would accept without question.
  - 70-89  : clear semantic match with meaningful lexical or structural drift (synonyms, reordering).
  - 50-69  : the policy claim plausibly covers the requirement but leaves room for interpretation.
  - 30-49  : tenuous — shares topic but the covered scope is narrower / broader / uncertain.
  - 0-29   : weak — only surface overlap; a regulator would likely push back.
For UNRELATED verdicts, omit `confidence`.

Return a JSON array with one entry per candidate (in the same order), each object shaped:
  {{"index": <0-based index>, "verdict": "MATCH" | "CONTRADICTION" | "UNRELATED", "rationale": "<one short sentence>", "confidence": <0-100 integer, omit for UNRELATED>}}

Return ONLY the JSON array. No prose, no code fences."""
