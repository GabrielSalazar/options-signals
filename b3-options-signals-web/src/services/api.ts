import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export interface Signal {
    strategy: string;
    ticker: string;
    spot_price: number;
    signal_type: string;
    reason: string;
    recommendation: string;
    confidence_score: number;
    risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'UNLIMITED';
    risk_flags?: string[];
    technicals: {
        rsi: number;
        iv: number;
    };
    legs: Array<{
        symbol: string;
        strike: number;
        type: string;
        action: string;
    }>;
    timestamp: string;
    option_symbol?: string; // Optional if coming from different structure
}

export const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const fetchSignals = async (ticker?: string): Promise<Signal[]> => {
    try {
        const params = ticker ? { ticker } : {};
        const response = await api.get<Signal[]>('/signals', { params });
        return response.data;
    } catch (error) {
        console.error('Error fetching signals:', error);
        return [];
    }
};
