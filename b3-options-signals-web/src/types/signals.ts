export interface Signal {
    strategy: string;
    ticker: string;
    option_symbol: string;
    strike: number;
    spot_price: number;
    type: string; // 'CALL' or 'PUT'
    reason: string;
    greeks?: {
        delta: number;
        gamma: number;
        theta: number;
        vega: number;
        rho: number;
    }
    entry_price?: number;
    recommended_action?: string;
    explanation?: string;
}

export interface ScanResponse {
    message: string;
    signals_found: number;
    results: Signal[];
}
