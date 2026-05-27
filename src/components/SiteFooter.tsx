import Link from "next/link"

export default function SiteFooter() {
    const year = new Date().getFullYear()

    return (
        <footer className="site-footer">
            <div className="site-footer-grid">
                {/* Col 1 — Brand */}
                <div>
                    <div className="site-footer-logo">
                        <div className="site-footer-logo-mark">B3</div>
                        <span className="site-footer-brand">Option Signals</span>
                    </div>
                    <p className="site-footer-tagline">
                        Scanner automatizado de volatilidade e oportunidades em opções do mercado brasileiro.
                    </p>
                </div>

                {/* Col 2 — Navegação */}
                <div>
                    <div className="site-footer-col-title">Plataforma</div>
                    <nav className="site-footer-links">
                        <Link href="/"               className="site-footer-link">Dashboard</Link>
                        <Link href="/scanner"        className="site-footer-link">Scanner</Link>
                        <Link href="/signals"        className="site-footer-link">Sinais</Link>
                        <Link href="/signals/sobre"  className="site-footer-link">Como funciona</Link>
                        <Link href="/analytics"      className="site-footer-link">Analytics</Link>
                    </nav>
                </div>

                {/* Col 3 — Recursos */}
                <div>
                    <div className="site-footer-col-title">Recursos</div>
                    <nav className="site-footer-links">
                        <a href={`${process.env.NEXT_PUBLIC_API_URL ?? ""}/docs`}
                           target="_blank" rel="noopener noreferrer"
                           className="site-footer-link">
                            API Docs
                        </a>
                        <a href={`${process.env.NEXT_PUBLIC_API_URL ?? ""}/health`}
                           target="_blank" rel="noopener noreferrer"
                           className="site-footer-link">
                            Status do Backend
                        </a>
                        <Link href="/backtest"  className="site-footer-link">Backtesting</Link>
                        <Link href="/alerts"    className="site-footer-link">Histórico de Alertas</Link>
                    </nav>
                </div>

                {/* Col 4 — Horário de mercado */}
                <div>
                    <div className="site-footer-col-title">Mercado B3</div>
                    <div className="site-footer-hours">
                        <div className="site-footer-hours-row">
                            <span className="site-footer-hours-label">Pregão</span>
                            <span className="site-footer-hours-value">10h–17h</span>
                        </div>
                        <div className="site-footer-hours-row">
                            <span className="site-footer-hours-label">After</span>
                            <span className="site-footer-hours-value">17h15–18h</span>
                        </div>
                        <div className="site-footer-hours-row">
                            <span className="site-footer-hours-label">Dias</span>
                            <span className="site-footer-hours-value">Seg–Sex</span>
                        </div>
                        <div className="site-footer-hours-row">
                            <span className="site-footer-hours-label">Fusos</span>
                            <span className="site-footer-hours-value">BRT (UTC−3)</span>
                        </div>
                    </div>
                </div>
            </div>

            <div className="site-footer-bottom">
                <span className="site-footer-copy">
                    © {year} B3 Option Signals. Todos os direitos reservados.
                </span>
                <span className="site-footer-disclaimer">
                    Dados para fins educacionais. Não constitui recomendação de investimento.
                    Opções envolvem risco de perda total do capital investido.
                </span>
            </div>
        </footer>
    )
}
