import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#534AB7',    // purple
        accent: '#EF9F27',     // amber
        success: '#00A67E',
      },
    },
  },
  plugins: [],
} satisfies Config;