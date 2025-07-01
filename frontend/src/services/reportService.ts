// frontend/src/services/reportService.ts
import apiClient from './api'; // Main axios client
import { AxiosError } from 'axios';

export interface Report {
    id: string; // Or number, depending on backend
    report_type: string; // e.g., "DAILY_SUMMARY", "WEEKLY_SUMMARY", "BACKTEST"
    generated_at: string; // ISO datetime string
    file_name?: string; // Optional: if backend provides it directly
    download_url_pdf?: string; // Optional: direct URL or needs to be constructed
    download_url_csv?: string; // Optional
    parameters?: Record<string, any>; // For backtest reports primarily
    status?: string; // e.g., "COMPLETED", "PENDING", "FAILED"
}

export interface GenerateSummaryReportRequest {
    report_type: "DAILY" | "WEEKLY"; // Example types
    // Add other params if needed, e.g., specific date for daily
}

export interface GenerateBacktestReportRequest { // Matches backend expectations more closely
    report_name?: string | null; // Optional name for the report
    strategy_name: string;
    tickers: string[]; // Pair of tickers [Y, X]
    start_date: string; // ISO Date string "YYYY-MM-DD"
    end_date: string;   // ISO Date string "YYYY-MM-DD"
    initial_capital?: number;
    z_score_window?: number;
    entry_z_threshold?: number;
    exit_z_threshold?: number;
    // Any other params the backend might expect within its `params` dict for generate_backtest_data
}

export interface TaskInfo { // Generic response for starting a task
    task_id: string;
    status: string; // e.g., "PENDING" or "RECEIVED"
    message?: string;
}


export const getGeneratedReports = async (): Promise<Report[]> => {
    try {
        // Assuming backend returns a list of report metadata
        const response = await apiClient.get<Report[]>('/reports/');
        return response.data;
    } catch (error) {
        const axiosError = error as AxiosError;
        throw new Error((axiosError.response?.data as any)?.detail || 'Failed to fetch reports list.');
    }
};

export const requestSummaryReportGeneration = async (
    params: GenerateSummaryReportRequest
): Promise<TaskInfo> => { // Backend might return a task ID
    try {
        const response = await apiClient.post<TaskInfo>('/reports/generate_summary', params);
        return response.data;
    } catch (error) {
        const axiosError = error as AxiosError;
        throw new Error((axiosError.response?.data as any)?.detail || 'Failed to request summary report generation.');
    }
};

export const requestBacktestReportGeneration = async (
    params: GenerateBacktestReportRequest
): Promise<TaskInfo> => { // Backend might return a task ID
    try {
        const response = await apiClient.post<TaskInfo>('/reports/generate_backtest', params);
        return response.data;
    } catch (error) {
        const axiosError = error as AxiosError;
        throw new Error((axiosError.response?.data as any)?.detail || 'Failed to request backtest report generation.');
    }
};

// Function to check task status (if backend provides such an endpoint for reports)
// This might leverage the existing /tasks/status/{task_id} if reports are Celery tasks
export const getReportTaskStatus = async (taskId: string): Promise<any> => {
    try {
        const response = await apiClient.get(`/tasks/status/${taskId}`); // Using existing task status ep
        return response.data;
    } catch (error) {
         const axiosError = error as AxiosError;
        throw new Error((axiosError.response?.data as any)?.detail || 'Failed to fetch report task status.');
    }
};
