import path from "path";
import { fileURLToPath } from "url";

// Paths must be anchored to this file so Tailwind still scans sources when
// `next dev` / PostCSS runs with a cwd other than `frontend/` (common in monorepos / IDE).
const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    path.join(__dirname, "app/**/*.{js,ts,jsx,tsx,mdx}"),
    path.join(__dirname, "components/**/*.{js,ts,jsx,tsx,mdx}"),
    path.join(__dirname, "lib/**/*.{js,ts,jsx,tsx,mdx}"),
  ],
  theme: {
    extend: {
      colors: {
        medical: {
          blue: "#1d4ed8",
          "blue-light": "#3b82f6",
          surface: "#f8fafc",
        },
      },
    },
  },
  plugins: [],
};
