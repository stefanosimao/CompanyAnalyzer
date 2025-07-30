import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Configure the development server
    proxy: {
      // Proxy API requests to your Flask backend
      "/upload": "http://127.0.0.1:5000",
      "/settings": "http://127.0.0.1:5000",
      "/history": "http://127.0.0.1:5000",
      "/report": "http://127.0.0.1:5000",
      "/status": "http://127.0.0.1:5000",
      "/pe_firms": "http://127.0.0.1:5000",
      "/download": "http://127.0.0.1:5000",
    },
    host: "127.0.0.1",
    port: 5173,
    watch: {
      usePolling: true,
    },
  },
  // Ensure JSX transformation for .jsx files
  esbuild: {
    jsxFactory: "React.createElement",
    jsxFragment: "React.Fragment",
  },
});
