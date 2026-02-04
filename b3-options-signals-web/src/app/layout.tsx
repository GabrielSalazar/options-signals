import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
    title: "B3 Option Signals",
    description: "Real-time opportunities in Brazilian Options",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="pt-BR">
            <body>{children}</body>
        </html>
    );
}
