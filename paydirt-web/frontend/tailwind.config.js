/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        field: {
          green: '#2d5a27',
          stripe: '#3d7a37',
        },
        board: {
          bg: '#D2691E',
          border: '#8B4513',
        },
        panel: {
          bg: '#F5DEB3',
          border: '#8B4513',
        },
        led: {
          bg: '#1a1a2e',
          red: '#ff6b6b',
          blue: '#4ecdc4',
          off: '#333',
        },
        dice: {
          black: '#1a1a1a',
          white: '#f0f0f0',
          red: '#cc0000',
          green: '#006600',
        },
      },
      fontFamily: {
        scoreboard: ['Orbitron', 'monospace'],
        heading: ['Roboto Condensed', 'sans-serif'],
        body: ['Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
