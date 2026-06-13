import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        mist: "#f4f6f8",
        teal: "#167d7f",
        coral: "#eb785c"
      },
      boxShadow: {
        card: "0 20px 50px rgba(23, 32, 51, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;
