import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

// Dev-mode proxy so the dashboard can call services by short paths and Vite
// forwards them to the right container in the docker-compose network. Each
// platform stub is reachable on its own port from the host; inside docker,
// the dashboard talks to the containers by service name.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api/harness": { target: "http://harness-walker:8096", changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/harness/, "") },
      "/api/ptp": { target: "http://ptp-operator-stub:8091", changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/ptp/, "") },
      "/api/metal3": { target: "http://metal3-bmo-stub:8092", changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/metal3/, "") },
      "/api/redfish": { target: "http://redfish-bmc-stub:8093", changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/redfish/, "") },
      "/api/smo": { target: "http://tmf921-smo-stub:8094", changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/smo/, "") },
      "/api/chat": { target: "http://harness-chat:8098", changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/chat/, "") },
    },
  },
});
