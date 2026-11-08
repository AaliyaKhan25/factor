import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#c5f26a",
          hover: "#b4e354",
          dark: "#3d5a0f",
          soft: "#eef9d3",
          light: "#f5fce8",
          glow: "rgba(197, 242, 106, 0.35)",
        },
        cream: {
          DEFAULT: "#f7f5ee",
          card: "#ffffff",
          dark: "#ede8db",
        },
        line: {
          DEFAULT: "#ebe7da",
          dark: "#d8d3c3",
        },
        ink: {
          DEFAULT: "#1c2415",
          soft: "#2f3e24",
          light: "#576b47",
        },
      },
      fontFamily: {
        sans: ["'Plus Jakarta Sans'", "system-ui", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        display: ["'Outfit'", "'Plus Jakarta Sans'", "system-ui", "sans-serif"],
        serif: ["'Outfit'", "'Plus Jakarta Sans'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      boxShadow: {
        soft: "0 4px 20px -2px rgba(28, 36, 21, 0.06)",
        card: "0 2px 12px rgba(28, 36, 21, 0.04), 0 1px 3px rgba(28, 36, 21, 0.02)",
        hover: "0 8px 28px -4px rgba(28, 36, 21, 0.1), 0 2px 6px rgba(28, 36, 21, 0.04)",
        glow: "0 0 24px rgba(197, 242, 106, 0.45)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "progress-stripes": "progress-stripes 1s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
