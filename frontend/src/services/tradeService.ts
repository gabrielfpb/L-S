// frontend/src/services/tradeService.ts
import apiClient from './api'; // Main axios client
import { AxiosError } from 'axios';

// Align with backend schemas (trade_schemas.py and models.py)
export interface AssetTicker { // Simplified Asset representation for trade display
    ticker: string;
    name?: string; // Optional: if backend sends it
}

export interface Trade { // Corresponds to TradeResponse schema from backend
    id: number;
    user_id?: number | null;
    asset1_ticker: string;
    asset2_ticker: string;
    trade_type: string;
    status: string;
    entry_datetime: string; // ISO string, will be new Date() on frontend
    entry_price_asset1?: number | null;
    entry_price_asset2?: number | null;
    entry_spread_or_ratio?: number | null;
    entry_zscore?: number | null;
    quantity_asset1: number;
    quantity_asset2: number;
    cointegrated_pair_id?: number | null;
    notes?: string | null;
    stop_loss_level?: number | null;
    take_profit_level?: number | null;
    exit_datetime?: string | null;
    exit_price_asset1?: number | null;
    exit_price_asset2?: number | null;
    exit_spread_or_ratio?: number | null;
    exit_zscore?: number | null;
    realized_pnl?: number | null;
    unrealized_pnl?: number | null; // Typically calculated by backend or on frontend periodically
    asset1?: AssetTicker | null; // Populated by backend
    asset2?: AssetTicker | null; // Populated by backend
}

export interface TradeCreateData { // Corresponds to TradeCreate schema
    asset1_ticker: string;
    asset2_ticker: string;
    trade_type?: string; // Defaults in backend/schema
    status?: string;     // Defaults in backend/schema
    entry_price_asset1?: number | null;
    entry_price_asset2?: number | null;
    entry_spread_or_ratio?: number | null;
    entry_zscore?: number | null;
    quantity_asset1: number;
    quantity_asset2: number;
    cointegrated_pair_id?: number | null;
    notes?: string | null;
    stop_loss_level?: number | null;
    take_profit_level?: number | null;
    user_id?: number | null; // Will be set by backend based on authenticated user
}

export interface TradeUpdateData { // Corresponds to TradeUpdate schema
    status?: string | null;
    exit_datetime?: string | null; // ISO string
    exit_price_asset1?: number | null;
    exit_price_asset2?: number | null;
    exit_spread_or_ratio?: number | null;
    exit_zscore?: number | null;
    realized_pnl?: number | null; // Backend might calculate this
    notes?: string | null;
    stop_loss_level?: number | null;
    take_profit_level?: number | null;
}

export const getTrades = async (skip: number = 0, limit: number = 100, userId?: number): Promise<Trade[]> => {
    try {
        const params: any = { skip, limit };
        // The backend route for GET /trades/ uses "userId" as query param alias
        if (userId) params.userId = userId;
        const response = await apiClient.get<Trade[]>('/trades/', { params });
        return response.data;
    } catch (error) {
        const axiosError = error as AxiosError;
        throw new Error((axiosError.response?.data as any)?.detail || 'Failed to fetch trades');
    }
};

export const createTrade = async (tradeData: TradeCreateData): Promise<Trade> => {
    try {
        const response = await apiClient.post<Trade>('/trades/', tradeData);
        return response.data;
    } catch (error) {
        const axiosError = error as AxiosError;
        throw new Error((axiosError.response?.data as any)?.detail || 'Failed to create trade');
    }
};

export const updateTrade = async (tradeId: number, tradeUpdateData: TradeUpdateData): Promise<Trade> => {
    try {
        const response = await apiClient.patch<Trade>(`/trades/${tradeId}`, tradeUpdateData);
        return response.data;
    } catch (error) {
        const axiosError = error as AxiosError;
        throw new Error((axiosError.response?.data as any)?.detail || 'Failed to update trade');
    }
};

export const getTradeById = async (tradeId: number): Promise<Trade> => {
    try {
        const response = await apiClient.get<Trade>(`/trades/${tradeId}`);
        return response.data;
    } catch (error) {
        const axiosError = error as AxiosError;
        throw new Error((axiosError.response?.data as any)?.detail || 'Failed to fetch trade details');
    }
};
