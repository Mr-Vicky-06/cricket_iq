import type {
  QueryRequest,
  QueryResponse,
  HealthReadyResponse,
  HealthLiveResponse,
} from './types';

export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(message: string, status: number = 500, detail?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export class CricketIQClient {
  private baseUrl: string;
  private defaultTimeoutMs: number;

  constructor(baseUrl?: string, defaultTimeoutMs: number = 30000) {
    this.baseUrl = (baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
    this.defaultTimeoutMs = defaultTimeoutMs;
  }

  private async fetchWithTimeout(
    url: string,
    options: RequestInit = {},
    timeoutMs: number = this.defaultTimeoutMs
  ): Promise<Response> {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeoutMs);

    const mergedSignal = options.signal;
    if (mergedSignal) {
      mergedSignal.addEventListener('abort', () => controller.abort());
    }

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });
      return response;
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        throw new ApiError('Request timed out while waiting for CricketIQ regulatory verification.', 408);
      }
      throw new ApiError('Unable to connect to CricketIQ backend. Please verify the service is running.', 503);
    } finally {
      clearTimeout(id);
    }
  }

  async queryRules(request: QueryRequest, signal?: AbortSignal): Promise<QueryResponse> {
    const endpoint = `${this.baseUrl}/v1/rules/query`;

    const response = await this.fetchWithTimeout(
      endpoint,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify(request),
        signal,
      },
      30000
    );

    if (!response.ok) {
      let errorDetail = '';
      try {
        const errorJson = await response.json();
        errorDetail = errorJson.detail || errorJson.error || JSON.stringify(errorJson);
      } catch {
        errorDetail = response.statusText;
      }
      throw new ApiError(`Rule query failed: ${errorDetail}`, response.status, errorDetail);
    }

    const data: QueryResponse = await response.json();
    return data;
  }

  async checkHealthReady(): Promise<HealthReadyResponse> {
    const endpoint = `${this.baseUrl}/health/ready`;
    const response = await this.fetchWithTimeout(endpoint, { method: 'GET' }, 5000);
    if (!response.ok) {
      throw new ApiError('Backend database is not ready.', response.status);
    }
    return response.json();
  }

  async checkHealthLive(): Promise<HealthLiveResponse> {
    const endpoint = `${this.baseUrl}/health/live`;
    const response = await this.fetchWithTimeout(endpoint, { method: 'GET' }, 5000);
    if (!response.ok) {
      throw new ApiError('Backend process is not alive.', response.status);
    }
    return response.json();
  }
}

export const apiClient = new CricketIQClient();
