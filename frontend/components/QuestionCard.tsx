"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { QuestionStatus, TQuestion } from "@/lib/schema";
import { StatusDot } from "@/components/StatusDot";

export function QuestionCard({
  question,
  status,
}: {
  question: TQuestion;
  status: QuestionStatus;
}) {
  const pathname = usePathname();
  const href = `/questions/${question.number}`;
  const isActive = pathname === href;

  return (
    <Link
      href={href}
      prefetch
      aria-current={isActive ? "page" : undefined}
      style={{
        display: "grid",
        gridTemplateColumns: "28px 18px 1fr",
        columnGap: "10px",
        alignItems: "start",
        padding: "11px 18px 11px 14px",
        borderBottom: "1px solid var(--color-rule)",
        position: "relative",
        background: isActive
          ? "color-mix(in oklch, var(--color-accent-wash) 40%, transparent)"
          : "transparent",
        color: "var(--color-ink)",
        transition: "background 90ms linear",
      }}
      className="group"
    >
      <span
        aria-hidden
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          bottom: 0,
          width: "2px",
          background: isActive ? "var(--color-accent)" : "transparent",
        }}
      />
      <span
        style={{
          fontVariantNumeric: "tabular-nums",
          fontSize: "var(--text-xs)",
          color: "var(--color-ink-muted)",
          paddingTop: "3px",
          textAlign: "right",
          fontWeight: 500,
          letterSpacing: "0.02em",
        }}
      >
        {question.number.toString().padStart(2, "0")}
      </span>

      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          height: "1.3em",
          paddingTop: "3px",
        }}
      >
        <StatusDot status={status} />
      </span>

      <span
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "4px",
          minWidth: 0,
        }}
      >
        <span
          style={{
            fontSize: "var(--text-sm)",
            lineHeight: 1.4,
            color: "var(--color-ink)",
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
            fontWeight: isActive ? 500 : 400,
          }}
        >
          {question.text}
        </span>
        {question.reference ? (
          <span
            style={{
              fontSize: "10px",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--color-ink-muted)",
              fontWeight: 600,
            }}
          >
            {question.reference}
          </span>
        ) : null}
      </span>
    </Link>
  );
}
