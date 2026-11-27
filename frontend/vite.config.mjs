import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

// Dev server proxies /api to the FastAPI backend on :7777
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "./src") } },
  build: {
    sourcemap: true,
    rollupOptions: {
      input: {
        main: "index.html",
        platform: "platform.html",
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:7777",
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov", "html"],
      exclude: ["src/components/ui/**", "src/test/**", "**/*.d.ts"],
      thresholds: { lines: 60, functions: 60, branches: 50 },
    },
  },
});
