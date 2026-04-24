import { UploadGate } from "@/components/UploadGate";

export default function Home() {
  return (
    <div
      className="flex h-full items-center justify-center px-10"
      style={{ background: "var(--color-surface-raised)" }}
    >
      <UploadGate />
      <div
        style={{
          maxWidth: "52ch",
          textAlign: "left",
        }}
      >
        <div
          style={{
            fontSize: "10px",
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: "var(--color-ink-muted)",
            fontWeight: 700,
            marginBottom: "10px",
          }}
        >
          No question selected
        </div>
        <h2
          style={{
            margin: 0,
            fontFamily: "var(--font-serif)",
            fontWeight: 500,
            fontSize: "var(--text-2xl)",
            lineHeight: 1.2,
            letterSpacing: "-0.01em",
            color: "var(--color-ink)",
          }}
        >
          Choose a question from the left to see the matched policy.
        </h2>
        <p
          style={{
            marginTop: "16px",
            fontSize: "var(--text-base)",
            lineHeight: 1.6,
            color: "var(--color-ink-muted)",
            maxWidth: "56ch",
          }}
        >
          The status dot reports whether Readily found a clear policy source
          (filled), detected a conflict between the questionnaire and the
          policy (contradiction), or could not surface any matching
          language (unmatched).
        </p>
      </div>
    </div>
  );
}
