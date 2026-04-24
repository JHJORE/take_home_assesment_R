import type { CSSProperties } from "react";

import type { QuestionStatus } from "@/lib/schema";

const STYLES: Record<QuestionStatus, { label: string; style: CSSProperties }> = {
  filled: {
    label: "Filled — matched with no contradictions",
    style: { background: "var(--color-accent)" },
  },
  contradiction: {
    label: "Contradiction detected",
    style: {
      background: "var(--color-warn)",
      boxShadow:
        "inset 0 0 0 2px color-mix(in oklch, var(--color-warn-ink) 60%, transparent)",
    },
  },
  unmatched: {
    label: "Unmatched — no policy source found",
    style: {
      background: "transparent",
      border: "1px solid var(--color-ink-faint)",
    },
  },
  unprocessed: {
    label: "Not yet processed",
    style: {
      background: "transparent",
      border: "1px dashed var(--color-ink-faint)",
    },
  },
};

export function StatusDot({
  status,
  size = 10,
}: {
  status: QuestionStatus;
  size?: number;
}) {
  const { label, style } = STYLES[status];
  return (
    <span
      aria-label={label}
      role="img"
      style={{
        display: "inline-block",
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: "999px",
        flexShrink: 0,
        ...style,
      }}
    />
  );
}
