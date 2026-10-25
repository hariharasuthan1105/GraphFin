/** Additive Phase 8 entry adapter. The 87 protected original files stay intact.
 * npm run dev -- --config vite.research.config.ts
 * npm run build -- --config vite.research.config.ts
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import original from "./vite.config.ts";

export default defineConfig({
  ...original,
  plugins: [
    {
      name: "graphfin-research-entry",
      enforce: "pre",
      resolveId(source, importer) {
        if (
          source === "./App.tsx" &&
          importer?.replaceAll("\\", "/").endsWith("/src/main.tsx")
        ) {
          return fileURLToPath(
            new URL("./src/ResearchApp.tsx", import.meta.url),
          );
        }
        return null;
      },
      transformIndexHtml: {
        order: "pre",
        handler() {
          return readFileSync(
            new URL("./research.html", import.meta.url),
            "utf8",
          );
        },
      },
    },
    ...(original.plugins ?? []),
  ],
});
