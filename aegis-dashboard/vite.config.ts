// aegis-dashboard/vite.config.ts

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite"; // <--- IMPORT THE PLUGIN

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(), // <--- ADD THE PLUGIN HERE
  ],
});
