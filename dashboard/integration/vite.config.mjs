import path from "node:path";
import { fileURLToPath } from "node:url";

const integrationRoot = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(integrationRoot, "../frontend");
const contractsRoot = path.resolve(integrationRoot, "../contracts");
const backendPort = Number.parseInt(process.env.DASHBOARD_BACKEND_PORT ?? "8765", 10);
const frontendPort = Number.parseInt(process.env.DASHBOARD_FRONTEND_PORT ?? "5173", 10);
const viteCacheDir = process.env.DASHBOARD_VITE_CACHE_DIR
  ? path.resolve(process.env.DASHBOARD_VITE_CACHE_DIR)
  : path.join(frontendRoot, "node_modules", ".vite");

if (!Number.isInteger(backendPort) || backendPort < 1 || backendPort > 65535) {
  throw new Error("DASHBOARD_BACKEND_PORT must be an integer from 1 through 65535");
}
if (!Number.isInteger(frontendPort) || frontendPort < 1 || frontendPort > 65535) {
  throw new Error("DASHBOARD_FRONTEND_PORT must be an integer from 1 through 65535");
}

export default {
  root: frontendRoot,
  cacheDir: viteCacheDir,
  server: {
    host: "127.0.0.1",
    port: frontendPort,
    strictPort: true,
    cors: false,
    headers: {
      "Content-Security-Policy": [
        "default-src 'self'",
        `connect-src 'self' ws://127.0.0.1:${frontendPort}`,
        "img-src 'self' data:",
        "style-src 'self' 'unsafe-inline'",
        "script-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "frame-ancestors 'none'",
      ].join("; "),
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
      "Cache-Control": "private, no-cache",
    },
    fs: { allow: [frontendRoot, contractsRoot] },
    proxy: {
      "/api": {
        target: `http://127.0.0.1:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
  build: {
    target: "es2022",
    sourcemap: true,
  },
};
