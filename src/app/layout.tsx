import type { Metadata } from "next";
import { DM_Sans, Lora, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import SiteNav from "@/components/SiteNav";
import TickerBar from "@/components/TickerBar";
import SiteFooter from "@/components/SiteFooter";
import { Toaster } from "react-hot-toast";

const dmSans = DM_Sans({
    subsets: ["latin"],
    variable: "--font-dm-sans",
    display: "swap",
});

const lora = Lora({
    subsets: ["latin"],
    variable: "--font-lora",
    display: "swap",
});

const jetBrainsMono = JetBrains_Mono({
    subsets: ["latin"],
    variable: "--font-jetbrains-mono",
    display: "swap",
});

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
            <body className={`${dmSans.variable} ${lora.variable} ${jetBrainsMono.variable} layout-container bg-dw-bg font-sans text-dw-ink`}>
                <AuthProvider>
                    <SiteNav />
                    <TickerBar />
                    {children}
                    <Toaster position="bottom-right" />
                    <SiteFooter />
                </AuthProvider>
            </body>
        </html>
    );
}
