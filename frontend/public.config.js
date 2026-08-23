/**
 * Runtime-resolved public configuration.
 *
 * Precedence: Nitro server env (runtime, no rebuild) -> VITE_* (baked at build
 * time) -> local dev default.
 *
 * `process` is read through a guard on purpose: this module is reachable from
 * the client bundle, and Vite only statically replaces `import.meta.env.VITE_*`
 * there. A bare `process.env.X` would throw `ReferenceError: process is not
 * defined` in the browser and blank the page.
 *
 * On the server the NITRO_* values are read at runtime; `src/routes/__root.tsx`
 * serialises the resolved object into the SSR'd HTML so the browser sees the
 * same values without a rebuild.
 */
const fromServerEnv = (key) =>
  typeof process !== "undefined" && process.env ? process.env[key] : undefined;

export default {
  apiBaseUrl:
    fromServerEnv("NITRO_API_BASE_URL") ||
    import.meta.env.VITE_API_BASE_URL ||
    "http://localhost:8000",
  apiKey: fromServerEnv("NITRO_API_KEY") || import.meta.env.VITE_API_KEY || "",
};
