/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    // Completely override default color palette to enforce exact tokens
    colors: {
      transparent: "transparent",
      current: "currentColor",
      canvas: "#0A0E12",
      surface: "#12181F",
      "surface-raised": "#1A222B",
      "surface-glass": "rgba(18, 24, 31, 0.60)",
      hairline: "#232B33",
      border: "#232B33",
      "border-glass": "rgba(255, 255, 255, 0.06)",
      text: {
        primary: "#EDEFF2",
        secondary: "#8B96A3",
        tertiary: "#5A6672",
      },
      accent: {
        primary: "#4589FF",
        graph: "#78A9FF",
      },
      status: {
        suspicious: "#FA4D56",
        normal: "#42BE65",
        warning: "#F1C21B",
      },
    },
    fontFamily: {
      sans: ['"Inter"', '"IBM Plex Sans"', "system-ui", "-apple-system", "sans-serif"],
      mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      display: ['"EB Garamond"', "Georgia", "serif"],
      stat: ['"Public Sans"', '"IBM Plex Sans"', "sans-serif"],
      section: ['"IBM Plex Sans"', "sans-serif"],
    },
    fontSize: {
      xs: ["12px", { lineHeight: "16px" }],
      sm: ["14px", { lineHeight: "20px" }],
      base: ["16px", { lineHeight: "24px" }],
      lg: ["20px", { lineHeight: "28px" }],
      xl: ["28px", { lineHeight: "36px" }],
      "2xl": ["40px", { lineHeight: "48px" }],
      "3xl": ["56px", { lineHeight: "64px" }],
    },
    fontWeight: {
      normal: "400",
      medium: "500",
      semibold: "600",
    },
    borderRadius: {
      none: "0px",
      DEFAULT: "4px",
      sm: "2px",
      md: "4px",
      lg: "6px",
    },
    extend: {
      transitionDuration: {
        DEFAULT: "130ms",
      },
    },
  },
  plugins: [],
};
