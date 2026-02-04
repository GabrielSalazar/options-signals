export interface Signal {
    strategy: string;
    ticker: string;
    option_symbol: string;
    spot_price: number;
    signal_type: string;
    reason: string;
    timestamp: string;
    recommendation?: string; // Backend sends this
    recommended_action?: string; // Fallback or alternative
    risk_level: string;
    // Optional fields if we enhance backend later
    greeks?: {
        delta: number;
        gamma: number;
        theta: number;
        vega: number;
        rho: number;
    }
}

export interface ScanResponse {
    message: string;
    signals_found: number;
    results: Signal[];
}
