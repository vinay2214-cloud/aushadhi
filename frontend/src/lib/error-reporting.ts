/**
 * Runtime error reporting hook-point.
 *
 * Errors are logged locally; wire this to a real collector (Sentry, Cloud
 * Error Reporting) when one exists. Kept as a single function so the call
 * sites in the router never need to change.
 */
export function reportRuntimeError(error: unknown, context: Record<string, unknown> = {}) {
  console.error("[aushadhi] runtime error", error, context);
}
