import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        teal: { DEFAULT: "#1B998B", dark: "#147a6e" },
        // ألوان قابلة للتبديل فاتح/داكن (مرتبطة بمتغيّرات CSS في globals.css)
        sand: "var(--bg)",
        surface: "var(--surface)",
        ink: "var(--ink)",
        muted: "var(--muted)",
        line: "var(--line)",
        soft: "var(--soft)",
        accent: "#E08A3C",
        sky: "#3C7DD9",
      },
      fontFamily: {
        sans: ["var(--font-cairo)", "Tahoma", "Arial", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
