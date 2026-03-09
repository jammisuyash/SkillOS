import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  define: {
    "window.SKILLOS_API": JSON.stringify(process.env.VITE_API_URL || "http://localhost:8000"),
  },
});
