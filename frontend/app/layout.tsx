import type { Metadata } from "next";
import { Public_Sans, Literata } from "next/font/google";

import { getQuestionRows, getSources } from "@/lib/api";
import { QuestionList } from "@/components/QuestionList";

import "./globals.css";

const publicSans = Public_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-public-sans",
  display: "swap",
});

const literata = Literata({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
  variable: "--font-literata",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Readily — Questionnaire ↔ Policy",
  description:
    "Read-only view of regulatory questionnaire answers mapped to policy sources.",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [rows, sources] = await Promise.all([
    getQuestionRows(),
    getSources(),
  ]);

  const counts = rows.reduce(
    (acc, r) => {
      acc[r.status] = (acc[r.status] ?? 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  const referenceSet = new Set(
    rows.map((r) => r.question.reference).filter(Boolean),
  );
  const primaryReference =
    referenceSet.size === 1 ? [...referenceSet][0] : null;

  return (
    <html lang="en" className={`${publicSans.variable} ${literata.variable}`}>
      <body
        style={{
          fontFamily:
            "var(--font-public-sans), var(--font-sans)",
        }}
      >
        <div className="flex h-dvh w-full">
          <aside
            className="flex h-full flex-col border-r"
            style={{
              width: "420px",
              minWidth: "420px",
              borderColor: "var(--color-rule)",
              background: "var(--color-surface)",
            }}
          >
            <header
              className="flex flex-col gap-1 border-b px-5 py-4"
              style={{ borderColor: "var(--color-rule)" }}
            >
              <div
                className="flex items-center gap-2"
                style={{ fontSize: "var(--text-xs)" }}
              >
                <span
                  style={{
                    letterSpacing: "0.18em",
                    textTransform: "uppercase",
                    color: "var(--color-ink-muted)",
                    fontWeight: 600,
                  }}
                >
                  Readily
                </span>
                {sources.usingSample ? (
                  <span
                    style={{
                      fontSize: "10px",
                      letterSpacing: "0.12em",
                      textTransform: "uppercase",
                      color: "var(--color-warn-ink)",
                      background: "var(--color-warn-wash)",
                      padding: "1px 6px",
                      borderRadius: "2px",
                      fontWeight: 600,
                    }}
                    title="data/ is empty — sample fixture is rendered. Run `readily run` to replace."
                  >
                    Sample
                  </span>
                ) : null}
              </div>
              <h1
                className="m-0"
                style={{
                  fontFamily: "var(--font-serif)",
                  fontWeight: 500,
                  fontSize: "var(--text-lg)",
                  letterSpacing: "-0.01em",
                  color: "var(--color-ink)",
                }}
              >
                Questionnaire
              </h1>
              <p
                className="m-0"
                style={{
                  color: "var(--color-ink-muted)",
                  fontSize: "var(--text-xs)",
                }}
              >
                {primaryReference ? (
                  <>
                    <span style={{ fontWeight: 600 }}>{primaryReference}</span>
                    <span aria-hidden> · </span>
                  </>
                ) : null}
                {rows.length} question{rows.length === 1 ? "" : "s"}
              </p>
            </header>

            <QuestionList rows={rows} />

            <footer
              className="mt-auto flex items-center gap-4 border-t px-5 py-3"
              style={{
                borderColor: "var(--color-rule)",
                fontSize: "10px",
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: "var(--color-ink-muted)",
                fontWeight: 600,
              }}
            >
              <Legend label="Filled" count={counts.filled ?? 0} tone="accent" />
              <Legend
                label="Contradiction"
                count={counts.contradiction ?? 0}
                tone="warn"
              />
              <Legend
                label="Unmatched"
                count={counts.unmatched ?? 0}
                tone="muted"
              />
            </footer>
          </aside>

          <main
            className="relative flex-1 overflow-hidden"
            style={{ background: "var(--color-surface-raised)" }}
          >
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}

function Legend({
  label,
  count,
  tone,
}: {
  label: string;
  count: number;
  tone: "accent" | "warn" | "muted";
}) {
  const toneMap = {
    accent: "var(--color-accent)",
    warn: "var(--color-warn)",
    muted: "var(--color-ink-faint)",
  } as const;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        aria-hidden
        style={{
          display: "inline-block",
          width: "8px",
          height: "8px",
          borderRadius: "999px",
          background: tone === "muted" ? "transparent" : toneMap[tone],
          border:
            tone === "muted" ? `1px solid ${toneMap[tone]}` : "none",
        }}
      />
      <span>
        {label} {count > 0 ? count : ""}
      </span>
    </span>
  );
}
