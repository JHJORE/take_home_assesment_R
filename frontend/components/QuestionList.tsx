"use client";

import type { Row } from "@/lib/api";
import { QuestionCard } from "@/components/QuestionCard";

export function QuestionList({ rows }: { rows: Row[] }) {
  return (
    <nav
      aria-label="Questionnaire items"
      style={{
        flex: 1,
        overflowY: "auto",
        overflowX: "hidden",
      }}
    >
      <ol
        style={{
          listStyle: "none",
          padding: 0,
          margin: 0,
        }}
      >
        {rows.map((r) => (
          <li key={r.question.number}>
            <QuestionCard question={r.question} status={r.status} />
          </li>
        ))}
      </ol>
    </nav>
  );
}
