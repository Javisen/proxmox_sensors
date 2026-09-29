import { defineConfig } from "astro/config";

export default defineConfig({
  output: "static",
  trailingSlash: "always",
  site: "https://proxmox-sensors.es",
  base: "/",
});
