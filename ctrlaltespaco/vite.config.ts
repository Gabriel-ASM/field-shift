import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// In development the API runs elsewhere; these paths are forwarded to it.
// In production the API serves this build itself, so the front always calls same-origin paths.
const API_PATHS = ["/config", "/profiles", "/runs", "/geo", "/contracts", "/health"];

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const api = env.FIELD_SHIFT_API ?? "http://127.0.0.1:8000";
  return {
    plugins: [react()],
    // The build this bundle belongs to (the commit, set by the image build); compared with GET /config `version`.
    define: { __FIELD_SHIFT_VERSION__: JSON.stringify(env.FIELD_SHIFT_VERSION || "dev") },
    server: { proxy: Object.fromEntries(API_PATHS.map((path) => [path, api])) },
  };
});
