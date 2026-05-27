import axios from 'axios';

const BACKEND_URL = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

const api = axios.create({
    baseURL: BACKEND_URL,
});

// Single-ticker scan — returns { sinal: Signal | null }
export const fetchScan = async (ticker: string, filters: any = {}) => {
    const response = await api.post(`/signals/scan/${ticker}`, null, {
        params: filters
    });
    return response.data;
};

// Batch scan — sends tickers array, returns { data: Signal[] }
// Backend: POST /signals/scan/all (no body, scans ATIVOS_B3)
// For custom tickers, uses SSE stream endpoint instead
export const fetchBatchScanAll = async () => {
    const response = await api.post('/signals/scan/all');
    return response.data;
};

export const fetchAnalytics = async (ticker: string) => {
    const response = await api.get(`/signals/analytics/${ticker}`);
    return response.data;
};

export const fetchStrategies = async () => {
    const response = await api.get('/signals/strategies');
    return response.data;
};

export interface BacktestParams {
    ticker: string;
    start_date: string;
    end_date: string;
}

export interface BacktestMetrics {
    win_rate: number;
    total_return: number;
    max_drawdown: number;
    sharpe_ratio: number;
    trades: number;
}

export interface BacktestResponse {
    sinais: number;
    metrics: BacktestMetrics | null;
    equity_curve: number[];
    data: Record<string, unknown>[];
}

export const runBacktest = async (params: BacktestParams): Promise<BacktestResponse> => {
    const response = await api.post('/backtest/run', params);
    return response.data;
};

export const fetchBacktestStrategies = async () => {
    const response = await api.get('/backtest/strategies');
    return response.data;
};

export const fetchSignalHistory = async (
    limit = 50,
    ticker?: string,
    tipo_sinal?: string,
): Promise<import('@/types/signals').Signal[]> => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (ticker) params.set('ticker', ticker);
    if (tipo_sinal) params.set('tipo_sinal', tipo_sinal);
    const response = await api.get(`/signals/history?${params}`);
    return (response.data.data ?? []) as import('@/types/signals').Signal[];
};

export interface TelegramConfig {
    token: string;
    chat_id: string;
}

export const getTelegramConfig = async (): Promise<TelegramConfig> => {
    const response = await api.get('/config/telegram');
    return response.data;
};

export const saveTelegramConfig = async (config: TelegramConfig) => {
    const response = await api.post('/config/telegram', config);
    return response.data;
};

// Returns the backend base URL for SSE (needs to be public/client-accessible)
export const getBackendUrl = () =>
    process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export default api;
