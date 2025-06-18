/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}", // This line tells Tailwind to scan all JS, TS, JSX, TSX files in src/
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}