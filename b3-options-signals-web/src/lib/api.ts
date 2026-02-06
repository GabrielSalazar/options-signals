import axios from 'axios';

const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000', // Python Backend
});

export const fetchScan = async (ticker: string) => {
    const response = await api.post(`/signals/scan/${ticker}`);
    return response.data;
};

export const fetchStrategies = async () => {
    const response = await api.get('/signals/strategies');
    return response.data;
};

export interface BacktestParams {
    ticker: string;
    strategy_name: string;
    days: number;
    initial_capital: number;
}

export const runBacktest = async (params: BacktestParams) => {
    const response = await api.post('/backtest/run', params);
    return response.data;
};

export const fetchBacktestStrategies = async () => {
    const response = await api.get('/backtest/strategies');
    return response.data;
};

export const fetchSignalHistory = async (limit: number = 50) => {
    const response = await api.get(`/signals/history?limit=${limit}`);
    return response.data;
};

export default api;
