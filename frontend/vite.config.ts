import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Port 3000, the frontend URL the backend and README expect
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: true,
  },
  preview: {
    port: 3000,
  },
  build: {
    // antd alone is ~1.1 MB minified; split vendors so they are cached separately from app code
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          antd: ["antd", "@ant-design/icons", "dayjs"],
          markdown: ["react-markdown", "remark-gfm"],
        },
      },
    },
  },
});
