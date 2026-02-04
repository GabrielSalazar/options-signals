import axios from 'axios';

const api = axios.create({
    baseURL: 'http://127.0.0.1:8000', // Python Backend
});

export const fetchScan = async (ticker: string) => {
    const response = await api.post(`/signals/scan/${ticker}`);
    return response.data;
};

export const fetchStrategies = async () => {
    const response = await api.get('/signals/strategies');
    return response.data;
};

export default api;
