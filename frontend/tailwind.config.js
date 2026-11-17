/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        pitch: {
          50: '#F0F7F4',
          100: '#DCEEE6',
          200: '#BCDECFC',
          500: '#1B6A48',
          700: '#124B33',
          800: '#0F3826', // Primary Brand Forest Pitch
          900: '#092318',
        },
        parchment: {
          50: '#FFFFFF',
          100: '#FBFBF9',
          200: '#F4F4F0',
          300: '#EAEAE4',
        },
        gold: {
          50: '#FDFBF5',
          100: '#FDF8EB',
          500: '#C59B27',
          600: '#A9811C',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
        serif: [
          'Merriweather',
          'Georgia',
          'Cambria',
          'serif',
        ],
        mono: [
          'JetBrains Mono',
          'SFMono-Regular',
          'Menlo',
          'monospace',
        ],
      },
    },
  },
  plugins: [],
}
