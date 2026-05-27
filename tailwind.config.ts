import type { Config } from "tailwindcss";

const config: Config = {
    darkMode: 'class',
    content: [
        "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                dw: {
                    white: "var(--dw-white)",
                    bg: "var(--dw-bg)",
                    "bg-soft": "var(--dw-bg-soft)",
                    "bg-card": "var(--dw-bg-card)",
                    "bg-dark": "var(--dw-bg-dark)",
                    ink: "var(--dw-ink)",
                    "ink-mid": "var(--dw-ink-mid)",
                    "ink-light": "var(--dw-ink-light)",
                    "ink-muted": "var(--dw-ink-muted)",
                    rule: "var(--dw-rule)",
                    "rule-soft": "var(--dw-rule-soft)",
                    blue: "var(--dw-blue)",
                    "blue-soft": "var(--dw-blue-soft)",
                    green: "var(--dw-green)",
                    yellow: "var(--dw-yellow)",
                    red: "var(--dw-red)",
                },
                background: "hsl(var(--background))",
                foreground: "hsl(var(--foreground))",
                border: "hsl(var(--border))",
                input: "hsl(var(--input))",
                ring: "hsl(var(--ring))",
                primary: {
                    DEFAULT: "hsl(var(--primary))",
                    foreground: "hsl(var(--primary-foreground))",
                },
                secondary: {
                    DEFAULT: "hsl(var(--secondary))",
                    foreground: "hsl(var(--secondary-foreground))",
                },
                destructive: {
                    DEFAULT: "hsl(var(--destructive))",
                    foreground: "hsl(var(--destructive-foreground))",
                },
                muted: {
                    DEFAULT: "hsl(var(--muted))",
                    foreground: "hsl(var(--muted-foreground))",
                },
                accent: {
                    DEFAULT: "hsl(var(--accent))",
                    foreground: "hsl(var(--accent-foreground))",
                },
                popover: {
                    DEFAULT: "hsl(var(--popover))",
                    foreground: "hsl(var(--popover-foreground))",
                },
                card: {
                    DEFAULT: "hsl(var(--card))",
                    foreground: "hsl(var(--card-foreground))",
                },
            },
            fontFamily: {
                sans: ['var(--font-dm-sans)'],
                serif: ['var(--font-lora)'],
                mono: ['var(--font-jetbrains-mono)'],
            },
            borderRadius: {
                lg: "var(--radius)",
                md: "calc(var(--radius) - 2px)",
                sm: "calc(var(--radius) - 4px)",
            },
        },
    },
    plugins: [],
};
export default config;
