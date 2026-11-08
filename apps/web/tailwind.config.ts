import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#c5f26a", hover: "#b4e354", dark: "#3d5a0f", soft: "#eef9d3" },
        cream: "#f7f5ee",
        line: "#ebe7da",
        ink: "#1c2415",
      },
      fontFamily: { serif: ["Fraunces", "Georgia", "ui-serif", "serif"] },
    },
  },
  plugins: [],
};

export default config;
