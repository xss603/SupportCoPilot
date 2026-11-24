/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#f5f7fb',
        surface: {
          50: '#f1f5f9',
          100: '#ffffff',
          200: '#ffffff',
          300: '#f8fafc',
          DEFAULT: '#ffffff',
        },
        border: '#e2e8f0',
        brand: {
          50: '#ecfdf5',
          500: '#10b981',
          600: '#059669',
          accent: '#6366f1',
        }
      },
      boxShadow: {
        card: '0 1px 2px rgba(15,23,42,0.04), 0 1px 3px rgba(15,23,42,0.06)',
        pop: '0 10px 30px -8px rgba(15,23,42,0.18)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'Courier New', 'monospace'],
      }
    },
  },
  plugins: [],
}
