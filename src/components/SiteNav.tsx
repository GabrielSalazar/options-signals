"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

const navLinks = [
    { href: "/",              label: "Dashboard"      },
    { href: "/scanner",       label: "Scanner"        },
    { href: "/signals",       label: "Sinais"         },
    { href: "/signals/sobre", label: "Metodologia"    },
    { href: "/estrategias",   label: "Estratégias"    },
    { href: "/portfolio",     label: "Portfólio"      },
    { href: "/backtest",      label: "Backtest"       },
    { href: "/analytics",     label: "Analytics"      },
    { href: "/alerts",        label: "Alertas"        },
]

export default function SiteNav() {
    const pathname = usePathname()

    return (
        <nav className="site-nav">
            {/* Logo */}
            <div className="flex items-center gap-3">
                <Link href="/" className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm bg-gradient-to-br from-dw-blue to-cyan-500 shadow-sm flex-shrink-0">
                        B3
                    </div>
                    <span className="font-serif font-bold text-lg text-dw-ink hidden sm:block">
                        Option Signals
                    </span>
                </Link>
                <span className="ml-1 px-2 py-0.5 bg-dw-blue-soft border border-dw-rule-soft rounded text-[10px] font-bold text-dw-blue uppercase tracking-wider hidden md:inline-block">
                    Real-time
                </span>
            </div>

            {/* Nav links */}
            <div className="site-nav-links hidden lg:flex">
                {navLinks.map(({ href, label }) => (
                    <Link
                        key={href}
                        href={href}
                        className={`nav-link ${pathname === href ? "active" : ""}`}
                    >
                        {label}
                    </Link>
                ))}
            </div>

        </nav>
    )
}
