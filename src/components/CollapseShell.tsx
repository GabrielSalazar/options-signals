"use client"

import { useState, useRef } from "react"

interface Pill {
    label: string
    variant: "pos" | "neg" | "neu" | "blue"
}

interface CollapseShellProps {
    icon: React.ReactNode
    iconVariant?: "charts" | "table" | "green"
    title: string
    pills?: Pill[]
    defaultOpen?: boolean
    children: React.ReactNode
}

export default function CollapseShell({
    icon,
    iconVariant = "charts",
    title,
    pills = [],
    defaultOpen = false,
    children,
}: CollapseShellProps) {
    const [open, setOpen] = useState(defaultOpen)
    const bodyRef = useRef<HTMLDivElement>(null)

    return (
        <div className="collapse-wrap">
            <button
                type="button"
                className="collapse-trigger"
                aria-expanded={open}
                onClick={() => setOpen((v) => !v)}
            >
                <div className={`ct-icon ct-icon-${iconVariant}`}>{icon}</div>
                <div className="ct-text">
                    <span className="ct-title">{title}</span>
                    {pills.length > 0 && (
                        <div className="ct-meta">
                            {pills.map((p, i) => (
                                <span key={i} className={`ct-pill ${p.variant}`}>{p.label}</span>
                            ))}
                        </div>
                    )}
                </div>
                <div className="ct-chevron">
                    <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="2,3.5 5,6.5 8,3.5" />
                    </svg>
                </div>
            </button>

            <div className={`collapse-body-grid${open ? " open" : ""}`}>
                <div ref={bodyRef} className="collapse-body-inner">
                    <div className="collapse-body-content">
                        {children}
                    </div>
                </div>
            </div>
        </div>
    )
}
