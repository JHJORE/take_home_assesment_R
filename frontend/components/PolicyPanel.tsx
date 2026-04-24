"use client";

import { useMemo, useState, type CSSProperties } from "react";

import type {
  TPolicyDoc,
  TQuestion,
  TQuestionClaimResult,
  TMatchRecord,
} from "@/lib/schema";
import { pdfUrl } from "@/lib/env";
import { PdfViewer } from "@/components/PdfViewer";

type Props = {
  question: TQuestion;
  results: TQuestionClaimResult[];
  policies: TPolicyDoc[];
};

type Ref = {
  kind: "match" | "contradiction";
  record: TMatchRecord;
};

function Sep() {
  return (
    <span aria-hidden style={{ color: "var(--color-ink-faint)" }}>
      ·
    </span>
  );
}

export function PolicyPanel({ question, results, policies }: Props) {
  const byCode = useMemo(
    () => new Map(policies.map((p) => [p.meta.code, p] as const)),
    [policies],
  );

  const refs: Ref[] = useMemo(() => {
    const out: Ref[] = [];
    for (const r of results) {
      if (r.best_match) out.push({ kind: "match", record: r.best_match });
      for (const c of r.contradictions) {
        out.push({ kind: "contradiction", record: c });
      }
    }
    return out;
  }, [results]);

  // TODO: multi-policy switcher — pick the first policy by appearance and
  // surface any others as a muted "(+N more)" note. No current fixture exercises
  // the cross-policy case, so we intentionally don't build a chooser yet.
  const policyCodes = useMemo(() => {
    const seen: string[] = [];
    for (const r of refs) {
      if (!seen.includes(r.record.policy_code)) seen.push(r.record.policy_code);
    }
    return seen;
  }, [refs]);

  const activePolicyCode = policyCodes[0] ?? null;
  const activePolicy = activePolicyCode
    ? byCode.get(activePolicyCode) ?? null
    : null;

  const activeRefs = useMemo(
    () => refs.filter((r) => r.record.policy_code === activePolicyCode),
    [refs, activePolicyCode],
  );

  const quotes = useMemo(
    () =>
      activeRefs.map((r) => ({
        text: r.record.policy_claim.source_text,
        kind: r.kind,
      })),
    [activeRefs],
  );

  const matchRefs = activeRefs.filter((r) => r.kind === "match");
  const conflictRefs = activeRefs.filter((r) => r.kind === "contradiction");
  const matchRange = confidenceRange(matchRefs);
  const conflictRange = confidenceRange(conflictRefs);

  // The initial focus: top-scoring MATCH (or top-scoring contradiction if the
  // question has no matches). The user can override this by clicking a
  // rationale entry — `selectedRef` takes precedence when set.
  const primary = useMemo(() => {
    const pool = matchRefs.length > 0 ? matchRefs : conflictRefs;
    if (pool.length === 0) return null;
    return pool.reduce((acc, cur) =>
      (cur.record.confidence ?? 0) > (acc.record.confidence ?? 0) ? cur : acc,
    );
  }, [matchRefs, conflictRefs]);
  const [selectedRef, setSelectedRef] = useState<Ref | null>(null);
  const activeRef = selectedRef ?? primary;
  const primaryQuote = activeRef?.record.policy_claim.source_text ?? "";
  const primaryPage = activeRef?.record.policy_claim.page ?? null;

  const hasMatches = activeRefs.length > 0;

  const pdfFileUrl = activePolicyCode ? pdfUrl(activePolicyCode) : "";
  const pdfAvailable = Boolean(
    activeRefs[0]?.record.policy_file_path || activePolicy?.meta.file_path,
  );

  return (
    <div
      key={question.number}
      className="panel-swap flex h-full flex-col overflow-hidden"
    >
      <QuestionHeader
        question={question}
        matchRange={matchRange}
        conflictRange={conflictRange}
        conflictCount={conflictRefs.length}
      />

      {hasMatches ? (
        <StatusBar
          refs={activeRefs}
          policyCode={activePolicyCode}
          policyTitle={
            activeRefs[0]?.record.policy_title ||
            activePolicy?.meta.title ||
            ""
          }
          extraPolicyCount={policyCodes.length - 1}
          activeRef={activeRef}
          onSelectRef={setSelectedRef}
        />
      ) : null}

      <div
        className="relative min-h-0 flex-1"
        style={{ background: "var(--color-surface)" }}
      >
        {hasMatches && pdfAvailable ? (
          <PdfViewer
            fileUrl={pdfFileUrl}
            quotes={quotes}
            primaryQuote={primaryQuote}
            primaryPage={primaryPage}
          />
        ) : (
          <EmptyPdfState
            title={hasMatches ? "Source PDF unavailable" : "No matching policy"}
            body={
              hasMatches
                ? "The matched policy is not on disk for this deployment."
                : "No policy passage was matched to this question. Re-run `readily judge` after updating the policy corpus, or review the question's claim decomposition."
            }
          />
        )}
      </div>
    </div>
  );
}

function QuestionHeader({
  question,
  matchRange,
  conflictRange,
  conflictCount,
}: {
  question: TQuestion;
  matchRange: [number, number] | null;
  conflictRange: [number, number] | null;
  conflictCount: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const text = question.text.trim();
  const truncatable = text.length > 180;

  return (
    <header
      className="shrink-0 border-b px-8 pb-3 pt-4"
      style={{ borderColor: "var(--color-rule)" }}
    >
      <div className="flex items-start justify-between gap-6">
        <div className="min-w-0 flex-1">
          <div
            className="flex flex-wrap items-center gap-2"
            style={{
              fontSize: "10px",
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "var(--color-ink-muted)",
              fontWeight: 600,
            }}
          >
            <span>Question {question.number}</span>
            {question.reference ? (
              <>
                <Sep />
                <span>{question.reference}</span>
              </>
            ) : null}
            {question.metadata.lob.length > 0 ? (
              <>
                <Sep />
                <span>{question.metadata.lob.join(" / ")}</span>
              </>
            ) : null}
          </div>
          <h2
            className="m-0 mt-1"
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: "var(--text-base)",
              lineHeight: 1.45,
              letterSpacing: "-0.005em",
              fontWeight: 500,
              color: "var(--color-ink)",
              maxWidth: "96ch",
              display: "-webkit-box",
              WebkitBoxOrient: "vertical",
              WebkitLineClamp: expanded ? "unset" : 2,
              overflow: "hidden",
            }}
          >
            {text}
          </h2>
          {truncatable ? (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              style={{
                marginTop: "4px",
                background: "transparent",
                border: "none",
                padding: 0,
                fontSize: "10px",
                letterSpacing: "0.14em",
                textTransform: "uppercase",
                color: "var(--color-accent-ink)",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              {expanded ? "Show less" : "Show more"}
            </button>
          ) : null}
        </div>

        <ConfidenceBadge
          matchRange={matchRange}
          conflictRange={conflictRange}
          conflictCount={conflictCount}
        />
      </div>
    </header>
  );
}

function ConfidenceBadge({
  matchRange,
  conflictRange,
  conflictCount,
}: {
  matchRange: [number, number] | null;
  conflictRange: [number, number] | null;
  conflictCount: number;
}) {
  if (matchRange === null && conflictRange === null) {
    return (
      <div
        className="shrink-0"
        style={{
          textAlign: "right",
          fontSize: "10px",
          letterSpacing: "0.14em",
          textTransform: "uppercase",
          color: "var(--color-ink-faint)",
          fontWeight: 600,
        }}
      >
        Unscored
      </div>
    );
  }

  // When there are matches, the headline number is the match confidence; any
  // conflicts show as a smaller chip beneath. When there are ONLY conflicts,
  // the headline becomes the conflict itself.
  if (matchRange) {
    return (
      <div
        className="shrink-0 flex flex-col items-end gap-1"
        style={{ fontVariantNumeric: "tabular-nums" }}
      >
        <ConfidenceNumber
          label="AI confidence"
          range={matchRange}
          tone="match"
        />
        {conflictRange ? (
          <ConflictChip count={conflictCount} range={conflictRange} />
        ) : null}
      </div>
    );
  }

  // Pure-contradiction case: no supporting match at all.
  return (
    <div
      className="shrink-0"
      style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}
    >
      <ConfidenceNumber
        label={conflictCount > 1 ? `${conflictCount} conflicts` : "Conflict"}
        range={conflictRange!}
        tone="conflict"
      />
    </div>
  );
}

function ConfidenceNumber({
  label,
  range,
  tone,
}: {
  label: string;
  range: [number, number];
  tone: "match" | "conflict";
}) {
  const toneInk =
    tone === "conflict"
      ? "var(--color-warn-ink)"
      : "var(--color-accent-ink)";
  const value = formatRange(range);
  return (
    <div
      style={{ textAlign: "right" }}
      aria-label={`${label} ${value} out of 100`}
    >
      <div
        style={{
          fontSize: "10px",
          letterSpacing: "0.14em",
          textTransform: "uppercase",
          color: toneInk,
          fontWeight: 700,
          marginBottom: "-2px",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: "var(--font-sans)",
          fontSize: "1.75rem",
          fontWeight: 600,
          color: toneInk,
          letterSpacing: "-0.02em",
          lineHeight: 1,
        }}
      >
        {value}
        <span
          style={{
            fontSize: "0.75rem",
            color: "var(--color-ink-muted)",
            fontWeight: 500,
            marginLeft: "2px",
          }}
        >
          /100
        </span>
      </div>
    </div>
  );
}

function ConflictChip({
  count,
  range,
}: {
  count: number;
  range: [number, number];
}) {
  return (
    <div
      className="inline-flex items-center gap-1.5"
      style={{
        fontSize: "10px",
        letterSpacing: "0.14em",
        textTransform: "uppercase",
        color: "var(--color-warn-ink)",
        fontWeight: 700,
        padding: "2px 8px",
        borderRadius: "999px",
        border: "1px solid var(--color-warn-ink)",
        background:
          "color-mix(in oklch, var(--color-warn) 14%, transparent)",
      }}
    >
      <span
        aria-hidden
        style={{
          display: "inline-block",
          width: "6px",
          height: "6px",
          borderRadius: "999px",
          background: "var(--color-warn-ink)",
        }}
      />
      {count} conflict{count === 1 ? "" : "s"} · {formatRange(range)}/100
    </div>
  );
}

function confidenceRange(refs: Ref[]): [number, number] | null {
  const scores = refs
    .map((r) => r.record.confidence)
    .filter((c): c is number => typeof c === "number");
  return scores.length ? [Math.min(...scores), Math.max(...scores)] : null;
}

function formatRange([lo, hi]: [number, number]): string {
  const a = Math.round(lo);
  const b = Math.round(hi);
  return a === b ? `${a}` : `${a}–${b}`;
}

function StatusBar({
  refs,
  policyCode,
  policyTitle,
  extraPolicyCount,
  activeRef,
  onSelectRef,
}: {
  refs: Ref[];
  policyCode: string | null;
  policyTitle: string;
  extraPolicyCount: number;
  activeRef: Ref | null;
  onSelectRef: (ref: Ref) => void;
}) {
  const [open, setOpen] = useState(false);
  const matchesLabel = `${refs.length} match${refs.length === 1 ? "" : "es"}`;

  const toggleButtonStyle: CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    background: "transparent",
    border: "none",
    padding: 0,
    margin: 0,
    fontSize: "10px",
    letterSpacing: "0.14em",
    textTransform: "uppercase",
    color: "var(--color-ink-muted)",
    fontWeight: 600,
    fontFamily: "inherit",
    cursor: "pointer",
    whiteSpace: "nowrap",
  };

  return (
    <div
      className="shrink-0 border-b"
      style={{
        borderColor: "var(--color-rule)",
        background: "var(--color-surface)",
      }}
    >
      <div
        className="flex items-center gap-3 px-8 py-2.5"
        style={{
          fontSize: "10px",
          letterSpacing: "0.14em",
          textTransform: "uppercase",
          color: "var(--color-ink-muted)",
          fontWeight: 600,
          minWidth: 0,
        }}
      >
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          style={toggleButtonStyle}
        >
          {matchesLabel}
        </button>

        {policyCode ? (
          <>
            <Sep />
            <span
              style={{
                fontFamily: "var(--font-mono)",
                letterSpacing: 0,
                textTransform: "none",
                color: "var(--color-ink)",
                fontWeight: 600,
              }}
              title={policyTitle || undefined}
            >
              {policyCode}
            </span>
          </>
        ) : null}

        {extraPolicyCount > 0 ? (
          <span style={{ color: "var(--color-ink-faint)" }}>
            (+{extraPolicyCount} more)
          </span>
        ) : null}

        <Sep />
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          style={{ ...toggleButtonStyle, gap: "6px" }}
        >
          <span>Rationale</span>
          <Chevron open={open} />
        </button>
      </div>

      {open ? (
        <RationaleList
          refs={refs}
          activeRef={activeRef}
          onSelectRef={onSelectRef}
        />
      ) : null}
    </div>
  );
}

function RationaleList({
  refs,
  activeRef,
  onSelectRef,
}: {
  refs: Ref[];
  activeRef: Ref | null;
  onSelectRef: (ref: Ref) => void;
}) {
  const items = refs.filter((r) => (r.record.rationale || "").trim().length > 0);
  if (items.length === 0) {
    return (
      <div
        className="border-t px-8 py-3"
        style={{
          borderColor: "var(--color-rule)",
          fontSize: "var(--text-sm)",
          color: "var(--color-ink-muted)",
        }}
      >
        No rationale recorded.
      </div>
    );
  }
  return (
    <ul
      className="m-0 list-none border-t p-0"
      style={{ borderColor: "var(--color-rule)" }}
    >
      {items.map((ref, i) => {
        const tone = ref.kind === "contradiction" ? "warn" : "accent";
        const toneInk =
          tone === "warn" ? "var(--color-warn-ink)" : "var(--color-accent-ink)";
        const toneColor =
          tone === "warn" ? "var(--color-warn)" : "var(--color-accent)";
        const pclaim = ref.record.policy_claim;
        const isActive = activeRef === ref;
        return (
          <li
            key={i}
            role="button"
            tabIndex={0}
            onClick={() => onSelectRef(ref)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelectRef(ref);
              }
            }}
            className="flex items-start gap-3 px-8 py-2.5 transition-colors"
            style={{
              borderBottom:
                i < items.length - 1 ? "1px solid var(--color-rule)" : "none",
              cursor: "pointer",
              background: isActive
                ? "color-mix(in oklch, var(--color-accent-wash) 55%, transparent)"
                : "transparent",
              outline: "none",
            }}
          >
            <span
              aria-hidden
              style={{
                display: "inline-block",
                width: "6px",
                height: "6px",
                borderRadius: "999px",
                background: toneColor,
                marginTop: "8px",
                flexShrink: 0,
              }}
            />
            <div className="min-w-0 flex-1">
              <div
                className="flex flex-wrap items-center gap-2"
                style={{
                  fontSize: "10px",
                  letterSpacing: "0.14em",
                  textTransform: "uppercase",
                  fontWeight: 700,
                  color: toneInk,
                }}
              >
                <span>{ref.kind === "contradiction" ? "Conflict" : "Match"}</span>
                {typeof pclaim.page === "number" ? (
                  <>
                    <Sep />
                    <span
                      style={{
                        textTransform: "none",
                        letterSpacing: 0,
                        color: "var(--color-ink-muted)",
                        fontWeight: 500,
                      }}
                    >
                      p. {pclaim.page}
                    </span>
                  </>
                ) : null}
                {ref.record.section ? (
                  <>
                    <Sep />
                    <span
                      style={{
                        textTransform: "none",
                        letterSpacing: 0,
                        color: "var(--color-ink-muted)",
                        fontWeight: 500,
                      }}
                    >
                      §&nbsp;{ref.record.section}
                    </span>
                  </>
                ) : null}
                {typeof ref.record.confidence === "number" ? (
                  <>
                    <Sep />
                    <span
                      style={{
                        textTransform: "none",
                        letterSpacing: 0,
                        color: "var(--color-ink-muted)",
                        fontWeight: 500,
                        fontVariantNumeric: "tabular-nums",
                      }}
                    >
                      {Math.round(ref.record.confidence)}/100
                    </span>
                  </>
                ) : null}
              </div>
              <p
                className="m-0 mt-1"
                style={{
                  fontFamily: "var(--font-serif)",
                  fontSize: "var(--text-sm)",
                  lineHeight: 1.55,
                  color: "var(--color-ink)",
                }}
              >
                {ref.record.rationale}
              </p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function Chevron({ open = false }: { open?: boolean }) {
  return (
    <svg
      width="10"
      height="10"
      viewBox="0 0 10 10"
      aria-hidden
      style={{
        transform: open ? "rotate(0deg)" : "rotate(-90deg)",
        transition: "transform 140ms cubic-bezier(0.2, 0, 0, 1)",
        flexShrink: 0,
      }}
    >
      <path
        d="M2 3 L5 6 L8 3"
        stroke="currentColor"
        strokeWidth="1.5"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function EmptyPdfState({ title, body }: { title: string; body: string }) {
  return (
    <div
      className="flex h-full items-center justify-center px-8"
      style={{ background: "var(--color-surface)" }}
    >
      <div
        style={{
          border: "1px dashed var(--color-rule-strong)",
          borderRadius: "var(--radius-md)",
          padding: "24px 28px",
          color: "var(--color-ink-muted)",
          maxWidth: "60ch",
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontWeight: 600,
            color: "var(--color-ink)",
            marginBottom: "6px",
            fontFamily: "var(--font-serif)",
            fontSize: "var(--text-md)",
          }}
        >
          {title}
        </div>
        <div style={{ fontSize: "var(--text-sm)", lineHeight: 1.55 }}>{body}</div>
      </div>
    </div>
  );
}
