import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// In development the API runs elsewhere; these paths are forwarded to it.
// In production the API serves this build itself, so the front always calls same-origin paths.
const API_PATHS = ["/config", "/profiles", "/runs", "/geo", "/contracts", "/health"];

export default defineConfig(({ mode }) => {
  const api = loadEnv(mode, process.cwd(), "").FIELD_SHIFT_API ?? "http://127.0.0.1:8000";
  return {
    plugins: [react()],
    server: { proxy: Object.fromEntries(API_PATHS.map((path) => [path, api])) },
  };
});
