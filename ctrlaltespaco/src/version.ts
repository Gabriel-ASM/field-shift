/** Build identity of this bundle, set by Vite from FIELD_SHIFT_VERSION (the commit, in the image); "dev" otherwise.
 *  The API reports its own in GET /config; a tab whose bundle is from another build must reload before it runs. */

declare const __FIELD_SHIFT_VERSION__: string | undefined;

export const DEV = "dev";
export const VERSION_HEADER = "X-Field-Shift-Version";
export const BUNDLE_VERSION: string = typeof __FIELD_SHIFT_VERSION__ === "string" && __FIELD_SHIFT_VERSION__ ? __FIELD_SHIFT_VERSION__ : DEV;

export const RELOAD_MESSAGE = "A new version of Field Shift is available. Reload the page.";

/** Only two known builds can disagree: "dev" (or nothing) on either side always matches, as in the API. */
export function outdated(bundle: string, server: string | null | undefined): boolean {
  return Boolean(server) && bundle !== DEV && server !== DEV && bundle !== server;
}
