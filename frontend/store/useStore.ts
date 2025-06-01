import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { 
  User, 
  Stream, 
  AnalyticsResult, 
  Bet, 
  WebSocketMessage,
  AlertEvent,
  ToastMessage 
} from '@/types';

// Auth Store
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setLoading: (isLoading) => set({ isLoading }),
      logout: () => set({ user: null, isAuthenticated: false }),
    }),
    {
      name: 'auth-store',
      partialize: (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
);

// Stream Store
interface StreamState {
  streams: Stream[];
  currentStream: Stream | null;
  isLoading: boolean;
  error: string | null;
  setStreams: (streams: Stream[]) => void;
  setCurrentStream: (stream: Stream | null) => void;
  addStream: (stream: Stream) => void;
  updateStream: (streamId: string, updates: Partial<Stream>) => void;
  removeStream: (streamId: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useStreamStore = create<StreamState>((set, get) => ({
  streams: [],
  currentStream: null,
  isLoading: false,
  error: null,
  setStreams: (streams) => set({ streams }),
  setCurrentStream: (currentStream) => set({ currentStream }),
  addStream: (stream) => set((state) => ({ streams: [...state.streams, stream] })),
  updateStream: (streamId, updates) => set((state) => ({
    streams: state.streams.map(stream => 
      stream.id === streamId ? { ...stream, ...updates } : stream
    ),
    currentStream: state.currentStream?.id === streamId 
      ? { ...state.currentStream, ...updates } 
      : state.currentStream
  })),
  removeStream: (streamId) => set((state) => ({
    streams: state.streams.filter(stream => stream.id !== streamId),
    currentStream: state.currentStream?.id === streamId ? null : state.currentStream
  })),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
}));

// Analytics Store
interface AnalyticsState {
  analytics: Record<string, AnalyticsResult>;
  summaries: Record<string, any>;
  isLoading: boolean;
  setAnalytics: (streamId: string, analytics: AnalyticsResult) => void;
  setSummary: (streamId: string, summary: any) => void;
  setLoading: (loading: boolean) => void;
  clearAnalytics: (streamId: string) => void;
}

export const useAnalyticsStore = create<AnalyticsState>((set) => ({
  analytics: {},
  summaries: {},
  isLoading: false,
  setAnalytics: (streamId, analytics) => set((state) => ({
    analytics: { ...state.analytics, [streamId]: analytics }
  })),
  setSummary: (streamId, summary) => set((state) => ({
    summaries: { ...state.summaries, [streamId]: summary }
  })),
  setLoading: (isLoading) => set({ isLoading }),
  clearAnalytics: (streamId) => set((state) => {
    const newAnalytics = { ...state.analytics };
    const newSummaries = { ...state.summaries };
    delete newAnalytics[streamId];
    delete newSummaries[streamId];
    return { analytics: newAnalytics, summaries: newSummaries };
  }),
}));

// Betting Store
interface BettingState {
  bets: Bet[];
  currentBet: Bet | null;
  isLoading: boolean;
  setBets: (bets: Bet[]) => void;
  addBet: (bet: Bet) => void;
  updateBet: (betId: string, updates: Partial<Bet>) => void;
  setCurrentBet: (bet: Bet | null) => void;
  setLoading: (loading: boolean) => void;
}

export const useBettingStore = create<BettingState>((set) => ({
  bets: [],
  currentBet: null,
  isLoading: false,
  setBets: (bets) => set({ bets }),
  addBet: (bet) => set((state) => ({ bets: [bet, ...state.bets] })),
  updateBet: (betId, updates) => set((state) => ({
    bets: state.bets.map(bet => bet.id === betId ? { ...bet, ...updates } : bet),
    currentBet: state.currentBet?.id === betId 
      ? { ...state.currentBet, ...updates } 
      : state.currentBet
  })),
  setCurrentBet: (currentBet) => set({ currentBet }),
  setLoading: (isLoading) => set({ isLoading }),
}));

// WebSocket Store
interface WebSocketState {
  socket: WebSocket | null;
  isConnected: boolean;
  messages: WebSocketMessage[];
  alerts: AlertEvent[];
  setSocket: (socket: WebSocket | null) => void;
  setConnected: (connected: boolean) => void;
  addMessage: (message: WebSocketMessage) => void;
  addAlert: (alert: AlertEvent) => void;
  clearMessages: () => void;
  clearAlerts: () => void;
}

export const useWebSocketStore = create<WebSocketState>((set) => ({
  socket: null,
  isConnected: false,
  messages: [],
  alerts: [],
  setSocket: (socket) => set({ socket }),
  setConnected: (isConnected) => set({ isConnected }),
  addMessage: (message) => set((state) => ({
    messages: [message, ...state.messages].slice(0, 100) // Keep last 100 messages
  })),
  addAlert: (alert) => set((state) => ({
    alerts: [alert, ...state.alerts].slice(0, 50) // Keep last 50 alerts
  })),
  clearMessages: () => set({ messages: [] }),
  clearAlerts: () => set({ alerts: [] }),
}));

// UI Store
interface UIState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  toasts: ToastMessage[];
  modals: Record<string, boolean>;
  setTheme: (theme: 'light' | 'dark') => void;
  setSidebarOpen: (open: boolean) => void;
  addToast: (toast: Omit<ToastMessage, 'id'>) => void;
  removeToast: (id: string) => void;
  openModal: (modalId: string) => void;
  closeModal: (modalId: string) => void;
  toggleModal: (modalId: string) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      theme: 'light',
      sidebarOpen: true,
      toasts: [],
      modals: {},
      setTheme: (theme) => set({ theme }),
      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
      addToast: (toast) => {
        const id = Date.now().toString();
        const newToast = { ...toast, id };
        set((state) => ({ toasts: [...state.toasts, newToast] }));
        
        // Auto-remove toast after duration
        setTimeout(() => {
          set((state) => ({ toasts: state.toasts.filter(t => t.id !== id) }));
        }, toast.duration || 4000);
      },
      removeToast: (id) => set((state) => ({
        toasts: state.toasts.filter(toast => toast.id !== id)
      })),
      openModal: (modalId) => set((state) => ({
        modals: { ...state.modals, [modalId]: true }
      })),
      closeModal: (modalId) => set((state) => ({
        modals: { ...state.modals, [modalId]: false }
      })),
      toggleModal: (modalId) => set((state) => ({
        modals: { ...state.modals, [modalId]: !state.modals[modalId] }
      })),
    }),
    {
      name: 'ui-store',
      partialize: (state) => ({ theme: state.theme, sidebarOpen: state.sidebarOpen }),
    }
  )
);

// Combined store selector hooks
export const useAppStore = () => ({
  auth: useAuthStore(),
  streams: useStreamStore(),
  analytics: useAnalyticsStore(),
  betting: useBettingStore(),
  websocket: useWebSocketStore(),
  ui: useUIStore(),
});

// Action helpers
export const showToast = (toast: Omit<ToastMessage, 'id'>) => {
  useUIStore.getState().addToast(toast);
};

export const showError = (message: string, title = 'Error') => {
  showToast({ type: 'error', title, message });
};

export const showSuccess = (message: string, title = 'Success') => {
  showToast({ type: 'success', title, message });
};

export const showWarning = (message: string, title = 'Warning') => {
  showToast({ type: 'warning', title, message });
};

export const showInfo = (message: string, title = 'Info') => {
  showToast({ type: 'info', title, message });
}; 