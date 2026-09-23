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
        // Dark navy forensic theme
        background: {
          DEFAULT: '#0a0e1a',
          light: '#0f1425',
          lighter: '#141a2f',
        },
        card: {
          DEFAULT: '#0f1425',
          light: '#141a2f',
          lighter: '#1a2140',
        },
        // Electric blue / cyan accents
        cyan: {
          50: '#e0f7ff',
          100: '#b3ecff',
          200: '#80dfff',
          300: '#4dd2ff',
          400: '#1ac5ff',
          500: '#00b8ff',
          600: '#0099cc',
          700: '#007a99',
          800: '#005c66',
          900: '#003d33',
        },
        // Secondary teal
        teal: {
          50: '#e0fdf7',
          100: '#b3fbec',
          200: '#80f9e0',
          300: '#4df7d4',
          400: '#1af5c8',
          500: '#00f3bc',
          600: '#00c297',
          700: '#009172',
          800: '#00614d',
          900: '#003128',
        },
        // Success green
        success: {
          DEFAULT: '#00ff88',
          light: '#33ff99',
          dark: '#00cc6a',
        },
        // Warning amber
        warning: {
          DEFAULT: '#ffaa00',
          light: '#ffbb33',
          dark: '#cc8800',
        },
        // High-risk red
        danger: {
          DEFAULT: '#ff3366',
          light: '#ff6688',
          dark: '#cc2952',
        },
        // Text colors
        text: {
          DEFAULT: '#ffffff',
          muted: '#a0aec0',
          dim: '#718096',
        },
        // Border colors
        border: {
          DEFAULT: '#1e3a5f',
          light: '#2a4a7f',
          lighter: '#3a5a9f',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.6s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite',
        'spin-slow': 'spin 3s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        glow: {
          '0%, 100%': { boxShadow: '0 0 5px rgba(0, 184, 255, 0.5)' },
          '50%': { boxShadow: '0 0 20px rgba(0, 184, 255, 0.8), 0 0 30px rgba(0, 184, 255, 0.4)' },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'glass': 'linear-gradient(135deg, rgba(15, 20, 37, 0.8) 0%, rgba(26, 33, 64, 0.6) 100%)',
        'glass-light': 'linear-gradient(135deg, rgba(20, 26, 47, 0.9) 0%, rgba(26, 33, 64, 0.7) 100%)',
      },
      backdropBlur: {
        'glass': '12px',
      },
    },
  },
  plugins: [],
}
