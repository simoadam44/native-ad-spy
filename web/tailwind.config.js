/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0A0A0F",
        card: "#13131A",
        border: "#1C1C27",
        primary: "#7C3AED",
        secondary: "#06B6D4",
        accent: "#F59E0B",
      },
      fontFamily: {
        syne: ["var(--font-syne)"],
        sans: ["var(--font-dm-sans)"],
      },
    },
  },
  plugins: [],
};
