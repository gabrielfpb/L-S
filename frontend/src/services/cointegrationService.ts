// frontend/src/services/cointegrationService.ts
import apiClient from './api'; // Main axios client
import { AxiosError } from 'axios';

// Types matching backend schemas (cointegration_schemas.py)

export interface IdentifiedPairData { // From backend schema IdentifiedPairData
    pair_yx: [string, string]; // [Y, X]
    adf_statistic: number;
    p_value: number;
    hedge_ratio_beta_x?: number | null;
    current_zscore_of_spread?: number | null;
    n_observations_in_test: number;
}

export interface IdentifyPairsRequest { // From backend schema IdentifyPairsRequest
    tickers: string[];
    p_value_threshold?: number;
    min_observations_for_test?: number;
    data_points_to_fetch?: number;
}

export interface IdentifyPairsApiResponse { // From backend schema IdentifyPairsResponse
    summary_message: string;
    requested_tickers_count: number;
    processed_tickers_with_data_count: number;
    found_pairs_count: number;
    pairs: IdentifiedPairData[];
    // parameters_used: IdentifyPairsRequest; // Backend echoes this
}

export interface PairZScoreRequest { // From backend schema PairZScoreParams
    ticker_y: string;
    ticker_x: string;
    window?: number;
    use_spread_with_eg_beta?: boolean;
}

export interface PairZScoreResponse { // From backend schema PairZScoreResponse
    pair_analyzed_yx: [string, string];
    value_type: string;
    current_value?: number | null;
    z_score?: number | null;
    series_mean_used_for_zscore?: number | null;
    series_std_dev_used_for_zscore?: number | null;
    hedge_ratio_beta_x_used?: number | null;
    error?: string | null;
}


export const identifyCointegratedPairs = async (
    params: IdentifyPairsRequest
): Promise<IdentifyPairsApiResponse> => {
    try {
        const response = await apiClient.post<IdentifyPairsApiResponse>('/cointegration/identify_pairs', params);
        return response.data;
    } catch (error) {
        const axiosError = error as AxiosError;
        const errorMessage = (axiosError.response?.data as any)?.detail ||
                             axiosError.message ||
                             'Failed to identify cointegrated pairs.';
        console.error("Error in identifyCointegratedPairs:", errorMessage, axiosError.response);
        throw new Error(errorMessage);
    }
};

export const getPairZScore = async (
    params: PairZScoreRequest
): Promise<PairZScoreResponse> => {
    try {
        const response = await apiClient.post<PairZScoreResponse>('/cointegration/zscore', params);
        return response.data;
    } catch (error) {
        const axiosError = error as AxiosError;
        const errorMessage = (axiosError.response?.data as any)?.detail ||
                             axiosError.message ||
                             'Failed to fetch pair Z-Score.';
        console.error("Error in getPairZScore:", errorMessage, axiosError.response);
        throw new Error(errorMessage);
    }
};

// import { Moment } from 'moment'; // Or use string for dates if not using moment

export interface HistoricalPairDataRequestFE { // Frontend might use different date types
    ticker_y: string;
    ticker_x: string;
    start_date: string; // ISO "YYYY-MM-DD"
    end_date: string;   // ISO "YYYY-MM-DD"
    z_score_window?: number;
}

export interface HistoricalPairDataResponseFE { // Matches backend response
    ticker_y: string;
    ticker_x: string;
    timestamps: string[]; // Datetime strings from backend
    prices_y: (number | null)[];
    prices_x: (number | null)[];
    spread: (number | null)[];
    spread_mean: (number | null)[];
    spread_std_dev_upper_1: (number | null)[];
    spread_std_dev_lower_1: (number | null)[];
    spread_std_dev_upper_2: (number | null)[];
    spread_std_dev_lower_2: (number | null)[];
    z_score: (number | null)[];
    calculated_hedge_ratio_beta_x?: number | null;
    error?: string | null;
}

export const getHistoricalPairData = async (
    params: HistoricalPairDataRequestFE
): Promise<HistoricalPairDataResponseFE> => {
    try {
        const response = await apiClient.post<HistoricalPairDataResponseFE>('/cointegration/pair_historical_data', params);
        return response.data;
    } catch (error) {
        const axiosError = error as AxiosError;
        const errorMessage = (axiosError.response?.data as any)?.detail ||
                             axiosError.message ||
                             'Failed to fetch historical pair data.';
        console.error("Error in getHistoricalPairData:", errorMessage, axiosError.response);
        throw new Error(errorMessage); // Rethrow to be caught by component
    }
};
