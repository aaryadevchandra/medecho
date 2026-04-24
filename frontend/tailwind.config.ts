import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
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

export default config;
