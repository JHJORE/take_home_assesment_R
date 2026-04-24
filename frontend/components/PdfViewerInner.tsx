"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  SpecialZoomLevel,
  Viewer,
  Worker,
  type DocumentLoadEvent,
  type LoadError,
  type Plugin,
  type PluginFunctions,
} from "@react-pdf-viewer/core";
import {
  searchPlugin,
  type HighlightArea,
  type RenderHighlightsProps,
} from "@react-pdf-viewer/search";

import "@react-pdf-viewer/core/lib/styles/index.css";
import "@react-pdf-viewer/search/lib/styles/index.css";

// Served from web/public via the postinstall copy, so the worker starts on
// the same origin and doesn't depend on a CDN round-trip.
const WORKER_URL = "/pdf.worker.min.js";

/**
 * Literal quote → regex. We have the exact source text, so we only allow
 * what PDF text-extraction actually changes: whitespace runs can collapse or
 * vanish entirely (pdf.js concatenates text-layer spans with no separator,
 * so a mid-quote line break in the PDF leaves zero whitespace in the scan
 * string — hence `\s*` rather than `\s+`), and straight/curly quotes are
 * interchangeable. No fuzzy fallback — every literal character must occur
 * in order in the page text.
 */
function quoteToPattern(q: string): RegExp {
  const normalized = q
    .replace(/[‘’‛′]/g, "'")
    .replace(/[“”‟″]/g, '"')
    .trim();
  const escaped = normalized
    .replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&")
    .replace(/'/g, "['‘’]")
    .replace(/"/g, '["“”]')
    .replace(/\s+/g, "\\s*");
  return new RegExp(escaped, "i");
}

export type QuoteKind = "match" | "contradiction";
export type TaggedQuote = { text: string; kind: QuoteKind };

type Rect = { left: number; top: number; width: number; height: number };
type KindedRect = Rect & { kind: QuoteKind; isSelected: boolean };

/**
 * react-pdf-viewer's search plugin emits one HighlightArea per text-layer
 * span a match crosses — a quote that spans 3 lines produces 3 stacked boxes.
 * We cluster areas that belong to the same match (same page + same keyword +
 * adjacent vertical position) and emit one union rectangle per cluster.
 *
 * We render everything in a single SVG so overlapping rects of the same kind
 * don't stack visually: group `opacity` composites children into an
 * offscreen buffer first, then blends the whole group in one pass.
 */
function renderUnionHighlights(
  props: RenderHighlightsProps,
  kindByRegexSource: Record<string, QuoteKind>,
  selectedSource: string | null,
) {
  const clusters = clusterHighlightAreas(props.highlightAreas);
  if (clusters.length === 0) return <></>;

  const rects: KindedRect[] = clusters.map((cluster) => {
    const anchor = cluster.areas[0];
    const kind = kindByRegexSource[anchor.keyword.source] ?? "match";
    const left = Math.min(...cluster.areas.map((a) => a.left));
    const top = Math.min(...cluster.areas.map((a) => a.top));
    const right = Math.max(...cluster.areas.map((a) => a.left + a.width));
    const bottom = Math.max(...cluster.areas.map((a) => a.top + a.height));
    return {
      left,
      top,
      width: right - left,
      height: bottom - top,
      kind,
      isSelected:
        selectedSource !== null && anchor.keyword.source === selectedSource,
    };
  });

  const matchRects = rects.filter((r) => r.kind === "match");
  const conflictRects = rects.filter((r) => r.kind === "contradiction");
  const selectedRects = rects.filter((r) => r.isSelected);

  const MATCH_FILL = "rgb(22, 140, 72)";
  const CONFLICT_FILL = "rgb(200, 38, 38)";

  return (
    <svg
      // `HighlightArea` coords are 0–100 percentages, so a 0–100 viewBox lets
      // us use them as SVG units directly.
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
      }}
    >
      {matchRects.length > 0 ? (
        <g opacity={0.26} fill={MATCH_FILL}>
          {matchRects.map((r, i) => (
            <rect
              key={i}
              x={r.left}
              y={r.top}
              width={r.width}
              height={r.height}
              rx={0.4}
            />
          ))}
        </g>
      ) : null}
      {conflictRects.length > 0 ? (
        <g opacity={0.26} fill={CONFLICT_FILL}>
          {conflictRects.map((r, i) => (
            <rect
              key={i}
              x={r.left}
              y={r.top}
              width={r.width}
              height={r.height}
              rx={0.4}
            />
          ))}
        </g>
      ) : null}
      {selectedRects.map((r, i) => (
        <rect
          key={`sel-${i}`}
          x={r.left}
          y={r.top}
          width={r.width}
          height={r.height}
          rx={0.4}
          fill="none"
          stroke={r.kind === "contradiction" ? CONFLICT_FILL : MATCH_FILL}
          strokeWidth={0.35}
          vectorEffect="non-scaling-stroke"
        />
      ))}
    </svg>
  );
}

/**
 * Group areas so each cluster is one logical match: same page, same keyword,
 * vertically near each other. Two areas are "near" if the vertical gap
 * between them is within ~1.5× the larger area's height — roughly one line.
 */
function clusterHighlightAreas(
  areas: HighlightArea[],
): { areas: HighlightArea[] }[] {
  const byKey = new Map<string, HighlightArea[]>();
  for (const a of areas) {
    const key = `${a.pageIndex}::${a.keyword.source}`;
    const bucket = byKey.get(key);
    if (bucket) bucket.push(a);
    else byKey.set(key, [a]);
  }

  const clusters: { areas: HighlightArea[] }[] = [];
  for (const bucket of byKey.values()) {
    bucket.sort((a, b) => a.top - b.top || a.left - b.left);
    let current: HighlightArea[] = [];
    let lastBottom = -Infinity;
    for (const a of bucket) {
      const gap = a.top - lastBottom;
      const lineHeight = a.height;
      if (current.length === 0 || gap <= lineHeight * 1.5) {
        current.push(a);
      } else {
        clusters.push({ areas: current });
        current = [a];
      }
      lastBottom = Math.max(lastBottom, a.top + a.height);
    }
    if (current.length > 0) clusters.push({ areas: current });
  }
  return clusters;
}

export type PdfViewerProps = {
  fileUrl: string;
  quotes: TaggedQuote[];
  primaryQuote: string;
  // 1-based page number of the top-scoring match, or null if unknown.
  // We translate to pdf.js's 0-based index at the boundary.
  primaryPage: number | null;
};

/**
 * Exposes `jumpToPage` via a ref so we can navigate after the document loads.
 * react-pdf-viewer's navigation lives in a separate package; inlining a tiny
 * plugin keeps us on the already-installed `@react-pdf-viewer/core` surface.
 */
function useJumpController() {
  const ref = useRef<{ jumpToPage: (i: number) => Promise<void> } | null>(null);
  const plugin = useMemo<Plugin>(
    () => ({
      install(fns: PluginFunctions) {
        ref.current = { jumpToPage: fns.jumpToPage };
      },
      uninstall() {
        ref.current = null;
      },
    }),
    [],
  );
  return { ref, plugin };
}

export default function PdfViewerInner({
  fileUrl,
  quotes,
  primaryQuote,
  primaryPage,
}: PdfViewerProps) {
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">(
    "loading",
  );

  const quotesKey = quotes.map((q) => `${q.kind}:${q.text}`).join("||");

  // The plugin's `keyword` prop is what actually paints highlights — it
  // subscribes to each page's text-layer render status and draws overlays
  // once the text is available.
  const { keywords, kindByRegexSource } = useMemo(() => {
    const list: RegExp[] = [];
    const kindMap: Record<string, QuoteKind> = {};
    for (const q of quotes) {
      const text = q.text.trim();
      if (!text) continue;
      const re = quoteToPattern(text);
      list.push(re);
      kindMap[re.source] = q.kind;
    }
    return { keywords: list, kindByRegexSource: kindMap };
    // `quotesKey` is the deep identity of `quotes`.
  }, [quotesKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // The `source` of the regex compiled from the currently-selected quote.
  // Used to mark the matching cluster with a solid ring so users can see
  // which rationale entry they clicked on.
  const selectedSource = primaryQuote ? quoteToPattern(primaryQuote).source : null;

  // searchPlugin() calls React hooks internally, so it must be invoked at
  // the top of render — not inside useMemo. The Viewer is still stable
  // across question changes because of `key={fileUrl}` below; only the
  // plugin's internal keyword list churns, which it's designed to handle.
  const search = searchPlugin({
    keyword: keywords,
    // We paint our own union-rect overlays via `renderHighlights` instead of
    // the default one-box-per-text-span style. A multi-line quote becomes a
    // single rectangle that tracks the shape of the text.
    renderHighlights: (props: RenderHighlightsProps) =>
      renderUnionHighlights(props, kindByRegexSource, selectedSource),
  });

  const jumper = useJumpController();

  // Reset loading state only when the file actually changes. Switching
  // questions within the same PDF must not re-show the loader.
  useEffect(() => {
    setLoadState("loading");
  }, [fileUrl]);

  // After the document is ready, jump to the claim's page. Also re-runs when
  // the user picks a different question for the same PDF.
  useEffect(() => {
    if (loadState !== "ready") return;
    if (primaryPage == null) return;
    const ctrl = jumper.ref.current;
    if (!ctrl) return;
    void ctrl.jumpToPage(Math.max(0, primaryPage - 1));
  }, [loadState, primaryPage, jumper.ref]);

  const handleDocumentLoad = (_e: DocumentLoadEvent) => {
    setLoadState("ready");
  };

  const renderError = (err: LoadError) => {
    setLoadState("error");
    return (
      <div
        style={{
          padding: "24px 28px",
          color: "var(--color-ink-muted)",
          fontSize: "var(--text-sm)",
          maxWidth: "60ch",
        }}
      >
        <div
          style={{
            fontWeight: 600,
            color: "var(--color-ink)",
            marginBottom: "4px",
          }}
        >
          Could not render source PDF
        </div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)" }}>
          {err?.message || "Unknown error"}
        </div>
      </div>
    );
  };

  // 0-based index for pdf.js; `initialPage` is only honored at first mount of
  // a given Viewer (hence `key={fileUrl}` below — same PDF reuses the mount).
  const initialPageIndex =
    primaryPage != null ? Math.max(0, primaryPage - 1) : undefined;

  return (
    <div
      className="readily-pdf-shell"
      style={{
        position: "relative",
        height: "100%",
        width: "100%",
        background: "var(--color-surface)",
      }}
    >
      {loadState === "loading" ? (
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
            pointerEvents: "none",
            zIndex: 1,
          }}
        >
          Loading source…
        </div>
      ) : null}
      <Worker workerUrl={WORKER_URL}>
        <Viewer
          key={fileUrl}
          fileUrl={fileUrl}
          plugins={[search, jumper.plugin]}
          defaultScale={SpecialZoomLevel.PageFit}
          initialPage={initialPageIndex}
          onDocumentLoad={handleDocumentLoad}
          renderError={renderError}
          theme="light"
        />
      </Worker>
    </div>
  );
}
