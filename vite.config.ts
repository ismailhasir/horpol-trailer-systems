import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

// 3D görüntüleyici lazy yüklenir; ama indirmesi ana bundle'ın çalışmasını
// beklemesin diye three.js ve Viewer chunk'larını HTML'de modulepreload ediyoruz.
function preloadViewer(): Plugin {
  return {
    name: "preload-viewer",
    apply: "build",
    transformIndexHtml(_html, ctx) {
      const files = Object.values(ctx.bundle ?? {})
        .filter((c) => c.type === "chunk" && (c.name === "three" || c.name === "Viewer"))
        .map((c) => c.fileName);
      return files.map((file) => ({
        tag: "link",
        attrs: { rel: "modulepreload", crossorigin: true, href: `/${file}` },
        injectTo: "head",
      }));
    },
  };
}

export default defineConfig({
  plugins: [react(), preloadViewer()],
  build: {
    target: "es2022",
    // three.js tek başına ~140 kB gzip; bilinçli olarak ayrı chunk.
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/three")) return "three";
        },
      },
    },
  },
});
