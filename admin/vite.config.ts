import fs from "node:fs";
import path from "node:path";
import {defineConfig} from "vite";
import react from "@vitejs/plugin-react";

function assembleAdminEntry() {
  return {
    name: "assemble-admin-entry",
    enforce: "pre" as const,
    load(id: string) {
      const normalized = id.split("?")[0];
      if (!normalized.endsWith(`${path.sep}src${path.sep}main.tsx`) && !normalized.endsWith("/src/main.tsx")) return null;
      const text = fs.readFileSync(normalized, "utf8");
      if (!text.includes("MAIN_TSX_ASSEMBLED_FROM_PARTS")) return null;
      const dir = path.join(path.dirname(normalized), "main_src");
      const names = fs.readdirSync(dir).filter((name) => name.startsWith("part-")).sort();
      return names.map((name) => fs.readFileSync(path.join(dir, name), "utf8")).join("");
    },
  };
}

export default defineConfig({plugins: [assembleAdminEntry(), react()]});
