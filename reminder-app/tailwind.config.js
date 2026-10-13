/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        app: "#0b0d12",
        surface: "#141821",
        "surface-2": "#1c2130",
        line: "#2a3142",
        fg: "#e8ebf2",
        muted: "#8a93a6",
        accent: { DEFAULT: "#7c5cff", soft: "#7c5cff26" },
        ok: "#34d399",
        warn: "#fbbf24",
        danger: "#f87171",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
