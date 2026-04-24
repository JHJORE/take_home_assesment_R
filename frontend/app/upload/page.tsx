"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { API_BASE } from "@/lib/env";

type Stage = "idle" | "dragging" | "extracting" | "error";

export default function UploadPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File | null | undefined) => {
      if (!file) return;
      const isPdf =
        file.type === "application/pdf" ||
        file.name.toLowerCase().endsWith(".pdf");
      if (!isPdf) return;
      setFileName(file.name);
      setStage("extracting");
      setError(null);

      const form = new FormData();
      form.append("file", file, file.name);
      try {
        const res = await fetch(`${API_BASE}/upload`, {
          method: "POST",
          body: form,
        });
        if (!res.ok) {
          throw new Error(`Upload failed: ${res.status} ${res.statusText}`);
        }
        sessionStorage.setItem("readily:uploaded", "1");
        router.push("/");
      } catch (err) {
        setStage("error");
        setError(err instanceof Error ? err.message : "Upload failed");
      }
    },
    [router],
  );

  const onDrop = useCallback(
    (event: React.DragEvent<HTMLButtonElement>) => {
      event.preventDefault();
      if (stage === "extracting") return;
      const file = event.dataTransfer.files?.[0];
      handleFile(file);
    },
    [handleFile, stage],
  );

  const onDragOver = useCallback(
    (event: React.DragEvent<HTMLButtonElement>) => {
      event.preventDefault();
      if (stage === "extracting") return;
      setStage("dragging");
    },
    [stage],
  );

  const onDragLeave = useCallback(
    (event: React.DragEvent<HTMLButtonElement>) => {
      event.preventDefault();
      if (stage === "extracting") return;
      setStage("idle");
    },
    [stage],
  );

  const openPicker = useCallback(() => {
    if (stage === "extracting") return;
    inputRef.current?.click();
  }, [stage]);

  const extracting = stage === "extracting";
  const dragging = stage === "dragging";

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        background: "var(--color-surface-raised)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px",
      }}
    >
      <div style={{ maxWidth: "56ch", width: "100%", textAlign: "left" }}>
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
          Step 1 — Questionnaire
        </div>
        <h1
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
          Upload your questionnaire
        </h1>
        <p
          style={{
            marginTop: "14px",
            marginBottom: "28px",
            fontSize: "var(--text-base)",
            lineHeight: 1.6,
            color: "var(--color-ink-muted)",
          }}
        >
          Readily will extract each question from the PDF and match it against
          your policy library. Drop the file below to get started.
        </p>

        <button
          type="button"
          onClick={openPicker}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          disabled={extracting}
          aria-busy={extracting}
          style={{
            display: "block",
            width: "100%",
            border: `1px dashed ${
              dragging ? "var(--color-accent)" : "var(--color-rule-strong)"
            }`,
            borderRadius: "var(--radius-md)",
            padding: "40px 28px",
            background: dragging
              ? "var(--color-surface)"
              : "var(--color-surface-raised)",
            color: "var(--color-ink-muted)",
            textAlign: "center",
            cursor: extracting ? "progress" : "pointer",
            transition: "border-color 120ms ease, background 120ms ease",
            font: "inherit",
          }}
        >
          {extracting ? (
            <DropzoneText title="Uploading…" subtitle={fileName ?? "questionnaire.pdf"} />
          ) : stage === "error" ? (
            <DropzoneText title="Upload failed" subtitle={error ?? "Unknown error"} tone="warn" />
          ) : (
            <DropzoneText title="Drag a PDF here" subtitle="or click to browse your files" />
          )}
        </button>

        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          style={{ display: "none" }}
          onChange={(event) => handleFile(event.target.files?.[0])}
        />

        <p
          style={{
            marginTop: "20px",
            fontSize: "var(--text-xs)",
            color: "var(--color-ink-muted)",
          }}
        >
          PDF only · up to 20 MB · processed locally
        </p>
      </div>
    </div>
  );
}

function DropzoneText({
  title,
  subtitle,
  tone = "default",
}: {
  title: string;
  subtitle: string;
  tone?: "default" | "warn";
}) {
  return (
    <>
      <div
        style={{
          fontFamily: "var(--font-serif)",
          fontSize: "var(--text-lg)",
          color: tone === "warn" ? "var(--color-warn-ink)" : "var(--color-ink)",
          marginBottom: "6px",
        }}
      >
        {title}
      </div>
      <div style={{ fontSize: "var(--text-sm)" }}>{subtitle}</div>
    </>
  );
}
