/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Veritas brand colors
        veritas: {
          primary: '#4ECDC4',
          secondary: '#45B7D1',
          accent: '#FF6B6B',
          dark: '#1a1a2e',
          darker: '#16162a',
          light: '#eaeaea',
        },
        // Node colors
        node: {
          query: '#FF6B6B',
          entity: '#4ECDC4',
          textUnit: '#45B7D1',
          community: '#96CEB4',
          document: '#FFEAA7',
          answer: '#DDA0DD',
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'trace-path': 'trace-path 1s ease-out forwards',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(78, 205, 196, 0.5)' },
          '100%': { boxShadow: '0 0 20px rgba(78, 205, 196, 0.8)' },
        },
        'trace-path': {
          '0%': { strokeDashoffset: '100%' },
          '100%': { strokeDashoffset: '0%' },
        }
      }
    },
  },
  plugins: [],
}
