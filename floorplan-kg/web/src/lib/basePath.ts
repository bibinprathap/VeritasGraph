// When the app is served behind a reverse-proxy subpath (e.g. nginx `/floorplan/`),
// Next.js basePath rewrites links and assets, but raw fetch() calls must be
// prefixed manually. NEXT_PUBLIC_BASE_PATH is inlined at build time.
export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

/** Prefix an absolute app path with the configured basePath. */
export const api = (path: string): string => `${BASE_PATH}${path}`;
