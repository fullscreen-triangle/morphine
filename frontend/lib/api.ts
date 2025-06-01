import axios, { AxiosInstance, AxiosResponse } from 'axios';
import {
  Stream,
  StreamStatus,
  StreamCreateForm,
  AnalyticsResult,
  StreamAnalytics,
  Bet,
  BettingActivity,
  BetPlaceForm,
  User,
  AuthResponse,
  LoginForm,
  RegisterForm,
  ApiResponse,
  PaginatedResponse,
} from '@/types';

class ApiClient {
  private client: AxiosInstance;
  private baseURL: string;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000';
    
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getAuthToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response: AxiosResponse) => response,
      (error) => {
        if (error.response?.status === 401) {
          this.clearAuthToken();
          // Redirect to login or handle auth error
          if (typeof window !== 'undefined') {
            window.location.href = '/auth/login';
          }
        }
        return Promise.reject(error);
      }
    );
  }

  private getAuthToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('auth_token');
    }
    return null;
  }

  private setAuthToken(token: string): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token);
    }
  }

  private clearAuthToken(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
    }
  }

  // Authentication Methods
  async login(credentials: LoginForm): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>('/api/auth/login', credentials);
    if (response.data.success && response.data.token) {
      this.setAuthToken(response.data.token);
    }
    return response.data;
  }

  async register(userData: RegisterForm): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>('/api/auth/register', userData);
    if (response.data.success && response.data.token) {
      this.setAuthToken(response.data.token);
    }
    return response.data;
  }

  async logout(): Promise<void> {
    this.clearAuthToken();
  }

  async getProfile(): Promise<ApiResponse<User>> {
    const response = await this.client.get<ApiResponse<User>>('/api/auth/profile');
    return response.data;
  }

  async updateProfile(updates: Partial<User>): Promise<ApiResponse<User>> {
    const response = await this.client.patch<ApiResponse<User>>('/api/auth/profile', updates);
    return response.data;
  }

  // Stream Methods
  async getStreams(): Promise<ApiResponse<Stream[]>> {
    const response = await this.client.get<ApiResponse<Stream[]>>('/api/streams');
    return response.data;
  }

  async getStream(streamId: string): Promise<ApiResponse<Stream>> {
    const response = await this.client.get<ApiResponse<Stream>>(`/api/streams/${streamId}`);
    return response.data;
  }

  async createStream(streamData: StreamCreateForm): Promise<ApiResponse<Stream>> {
    const response = await this.client.post<ApiResponse<Stream>>('/api/streams', streamData);
    return response.data;
  }

  async activateStream(streamId: string): Promise<ApiResponse<any>> {
    const response = await this.client.post<ApiResponse<any>>(`/api/streams/${streamId}/activate`);
    return response.data;
  }

  async deactivateStream(streamId: string): Promise<ApiResponse<any>> {
    const response = await this.client.post<ApiResponse<any>>(`/api/streams/${streamId}/deactivate`);
    return response.data;
  }

  async updateStream(streamId: string, updates: Partial<Stream>): Promise<ApiResponse<Stream>> {
    const response = await this.client.patch<ApiResponse<Stream>>(`/api/streams/${streamId}`, updates);
    return response.data;
  }

  async deleteStream(streamId: string): Promise<ApiResponse<any>> {
    const response = await this.client.delete<ApiResponse<any>>(`/api/streams/${streamId}`);
    return response.data;
  }

  // Analytics Methods
  async getLatestAnalytics(streamId: string): Promise<ApiResponse<AnalyticsResult>> {
    const response = await this.client.get<ApiResponse<AnalyticsResult>>(`/api/analytics/${streamId}/latest`);
    return response.data;
  }

  async getAnalyticsSummary(streamId: string): Promise<ApiResponse<StreamAnalytics>> {
    const response = await this.client.get<ApiResponse<StreamAnalytics>>(`/api/analytics/${streamId}/summary`);
    return response.data;
  }

  async processFrame(frameData: any): Promise<ApiResponse<any>> {
    const response = await this.client.post<ApiResponse<any>>('/api/analytics/process_frame', frameData);
    return response.data;
  }

  // Betting Methods
  async placeBet(betData: BetPlaceForm): Promise<ApiResponse<Bet>> {
    const response = await this.client.post<ApiResponse<Bet>>('/api/betting/place', betData);
    return response.data;
  }

  async getBet(betId: string): Promise<ApiResponse<Bet>> {
    const response = await this.client.get<ApiResponse<Bet>>(`/api/betting/${betId}`);
    return response.data;
  }

  async getUserBettingHistory(userId: string, limit = 50, offset = 0): Promise<PaginatedResponse<Bet>> {
    const response = await this.client.get<PaginatedResponse<Bet>>(
      `/api/betting/user/${userId}/history?limit=${limit}&offset=${offset}`
    );
    return response.data;
  }

  async getStreamBettingActivity(streamId: string, limit = 100): Promise<ApiResponse<BettingActivity>> {
    const response = await this.client.get<ApiResponse<BettingActivity>>(
      `/api/betting/stream/${streamId}/activity?limit=${limit}`
    );
    return response.data;
  }

  async cancelBet(betId: string): Promise<ApiResponse<Bet>> {
    const response = await this.client.post<ApiResponse<Bet>>(`/api/betting/${betId}/cancel`);
    return response.data;
  }

  // Health Check
  async healthCheck(): Promise<any> {
    const response = await this.client.get('/health');
    return response.data;
  }

  // WebSocket connection helper
  connectWebSocket(onMessage: (message: any) => void, onError?: (error: Event) => void): WebSocket | null {
    if (typeof window === 'undefined') return null;

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:3001/ws';
    const token = this.getAuthToken();
    
    const ws = new WebSocket(`${wsUrl}?token=${token}`);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        onMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (onError) {
        onError(error);
      }
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };
    
    return ws;
  }
}

// Create and export a singleton instance
export const apiClient = new ApiClient();

// Export individual method groups for convenience
export const auth = {
  login: (credentials: LoginForm) => apiClient.login(credentials),
  register: (userData: RegisterForm) => apiClient.register(userData),
  logout: () => apiClient.logout(),
  getProfile: () => apiClient.getProfile(),
  updateProfile: (updates: Partial<User>) => apiClient.updateProfile(updates),
};

export const streams = {
  getAll: () => apiClient.getStreams(),
  getById: (id: string) => apiClient.getStream(id),
  create: (data: StreamCreateForm) => apiClient.createStream(data),
  activate: (id: string) => apiClient.activateStream(id),
  deactivate: (id: string) => apiClient.deactivateStream(id),
  update: (id: string, updates: Partial<Stream>) => apiClient.updateStream(id, updates),
  delete: (id: string) => apiClient.deleteStream(id),
};

export const analytics = {
  getLatest: (streamId: string) => apiClient.getLatestAnalytics(streamId),
  getSummary: (streamId: string) => apiClient.getAnalyticsSummary(streamId),
  processFrame: (frameData: any) => apiClient.processFrame(frameData),
};

export const betting = {
  place: (data: BetPlaceForm) => apiClient.placeBet(data),
  getById: (id: string) => apiClient.getBet(id),
  getUserHistory: (userId: string, limit?: number, offset?: number) => 
    apiClient.getUserBettingHistory(userId, limit, offset),
  getStreamActivity: (streamId: string, limit?: number) => 
    apiClient.getStreamBettingActivity(streamId, limit),
  cancel: (id: string) => apiClient.cancelBet(id),
};

export const websocket = {
  connect: (onMessage: (message: any) => void, onError?: (error: Event) => void) =>
    apiClient.connectWebSocket(onMessage, onError),
};

export default apiClient; 