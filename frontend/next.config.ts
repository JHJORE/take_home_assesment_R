import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: __dirname,
  // pdfjs-dist transitively imports the Node `canvas` package for server-side
  // rendering. The browser path we use doesn't need it — alias it away so
  // neither Turbopack nor webpack tries to bundle the native module.
  turbopack: {
    resolveAlias: {
      canvas: { browser: "./stubs/empty.js" },
    },
  },
  webpack: (cfg) => {
    cfg.resolve = cfg.resolve ?? {};
    cfg.resolve.alias = {
      ...(cfg.resolve.alias as Record<string, string | false>),
      canvas: false,
    };
    return cfg;
  },
};

export default config;
