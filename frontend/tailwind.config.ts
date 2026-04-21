import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        paper: "#f8fafc",
        brand: "#0f766e",
        accent: "#c2410c"
      }
    }
  },
  plugins: []
};

export default config;
