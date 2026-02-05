export interface Signal {
    strategy: string;
    ticker: string;
    option_symbol: string;
    spot_price: number;
    signal_type: string;
    reason: string;
    timestamp: string;
    recommendation?: string;
    recommended_action?: string;
    risk_level: string; // 'LOW' | 'MEDIUM' | 'HIGH' | 'UNLIMITED'

    // New fields from Day 3
    confidence_score?: number;
    risk_flags?: string[];
    risk_info?: {
        level: string;
        icon: string;
        max_loss: string;
        description?: string;
    };
    technicals?: {
        rsi: number;
        iv: number;
    };
    legs?: Array<{
        symbol: string;
        strike: number;
        type: string; // 'call' | 'put'
        action: string; // 'BUY' | 'SELL'
        delta?: number;
    }>;

    greeks?: {
        delta: number;
        gamma: number;
        theta: number;
        vega: number;
        rho: number;
    };
}

export interface ScanResponse {
    message: string;
    signals_found: number;
    results: Signal[];
}
