import publicConfig from "../../public.config";

export type PublicConfig = { apiBaseUrl: string; apiKey: string };

/** Name of the global the SSR shell serialises the server's runtime config into. */
export const RUNTIME_CONFIG_GLOBAL = "__AUSHADHI_CONFIG__";

/**
 * Config as resolved on whichever side is asking.
 *
 * On the server this is `public.config.js` reading NITRO_* out of the live
 * process env. In the browser `process` does not exist, so the values arrive
 * via the global that `RootShell` writes into the SSR'd HTML; the build-time
 * VITE_* values in `public.config.js` are the fallback when the page was
 * served without SSR (e.g. a static preview).
 */
export function getPublicConfig(): PublicConfig {
  if (typeof window !== "undefined") {
    const injected = (window as unknown as Record<string, PublicConfig | undefined>)[
      RUNTIME_CONFIG_GLOBAL
    ];
    if (injected) {
      return {
        apiBaseUrl: injected.apiBaseUrl || publicConfig.apiBaseUrl,
        apiKey: injected.apiKey || publicConfig.apiKey,
      };
    }
  }
  return publicConfig;
}
