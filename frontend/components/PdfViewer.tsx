"use client";

import dynamic from "next/dynamic";

import type { PdfViewerProps } from "./PdfViewerInner";

/**
 * Thin client wrapper that defers the heavy pdfjs-dist + react-pdf-viewer
 * bundle to the browser. pdfjs-dist tries to `require("canvas")` when it
 * runs under Node, so keeping it out of the server bundle avoids that
 * resolution entirely and keeps the server payload small.
 */
const PdfViewerInner = dynamic(() => import("./PdfViewerInner"), {
  ssr: false,
  loading: () => (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "grid",
        placeItems: "center",
        color: "var(--color-ink-muted)",
        fontSize: "var(--text-xs)",
        letterSpacing: "0.14em",
        textTransform: "uppercase",
        fontWeight: 600,
      }}
    >
      Loading viewer…
    </div>
  ),
});

export function PdfViewer(props: PdfViewerProps) {
  return <PdfViewerInner {...props} />;
}
