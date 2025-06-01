// Stream Types
export interface Stream {
  id: string;
  title: string;
  description: string;
  status: 'active' | 'inactive' | 'pending' | 'error';
  settings: StreamSettings;
  created_at: string;
  updated_at?: string;
  thumbnail?: string;
  viewer_count?: number;
  analytics_enabled: boolean;
  betting_enabled: boolean;
}

export interface StreamSettings {
  enable_cv: boolean;
  enable_betting: boolean;
  quality: '720p' | '1080p' | '4K';
  frame_rate: number;
  analytics_interval: number;
  [key: string]: any;
}

export interface StreamStatus {
  stream_id: string;
  status: 'active' | 'inactive' | 'pending' | 'error';
  uptime?: number;
  viewers?: number;
  last_analytics?: string;
  health: 'healthy' | 'degraded' | 'critical';
}

// Analytics Types
export interface Detection {
  bbox: [number, number, number, number];
  confidence: number;
  class_id: number;
  center: [number, number];
}

export interface Track {
  track_id: number;
  position: [number, number];
  speed: number;
  age: number;
  bbox: [number, number, number, number];
}

export interface OpticalFlow {
  flow_magnitude: number;
  flow_direction: number;
  motion_intensity: number;
}

export interface MotionEnergy {
  motion_energy: number;
  active_regions: number;
}

export interface VibrioResult {
  timestamp: number;
  detections: Detection[];
  tracks: Track[];
  optical_flow: OpticalFlow;
  motion_energy: MotionEnergy;
  processing_time: number;
  total_detections: number;
  active_tracks: number;
}

export interface Landmark {
  x: number;
  y: number;
  visibility: number;
}

export interface BiomechanicsResult {
  joint_angles: Record<string, number>;
  velocities: Record<string, number[]>;
  center_of_mass?: [number, number];
}

export interface StrideMetrics {
  stride_frequency: number;
  stride_length: number;
  left_contacts: number;
  right_contacts: number;
  contact_asymmetry: number;
}

export interface MoriartyResult {
  timestamp: number;
  frame_idx: number;
  pose_detected: boolean;
  landmarks: Record<string, Landmark>;
  biomechanics?: BiomechanicsResult;
  stride_metrics?: StrideMetrics;
  processing_time: number;
}

export interface AnalyticsResult {
  stream_id: string;
  frame_idx: number;
  timestamp: number;
  vibrio?: VibrioResult;
  moriarty?: MoriartyResult;
  processing_time: number;
}

export interface StreamAnalytics {
  stream_id: string;
  start_time: string;
  end_time?: string;
  total_frames: number;
  total_detections: number;
  unique_tracks: number;
  average_speed: number;
  max_speed: number;
  pose_detection_rate: number;
  average_processing_time: number;
}

// Betting Types
export interface Bet {
  id: string;
  user_id: string;
  stream_id: string;
  bet_type: string;
  amount: number;
  odds: number;
  prediction: any;
  timestamp: number;
  status: 'pending' | 'active' | 'won' | 'lost' | 'cancelled';
  created_at: string;
  settled_at?: string;
  payout?: number;
}

export interface BettingOpportunity {
  stream_id: string;
  timestamp: number;
  opportunity_type: 'speed_milestone' | 'pose_event' | 'motion_pattern';
  description: string;
  confidence: number;
  related_track_id?: number;
  metadata: Record<string, any>;
}

export interface BettingActivity {
  recent_bets: Bet[];
  statistics: {
    total_bets: number;
    total_amount: number;
    active_bets: number;
  };
}

// User Types
export interface User {
  id: string;
  username: string;
  email: string;
  created_at: string;
  last_login?: string;
  is_active: boolean;
  profile?: UserProfile;
}

export interface UserProfile {
  avatar?: string;
  bio?: string;
  location?: string;
  website?: string;
  social_links?: Record<string, string>;
}

export interface AuthResponse {
  success: boolean;
  user?: User;
  token?: string;
  error?: string;
  message?: string;
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'analytics' | 'stream_status' | 'betting' | 'alert';
  stream_id?: string;
  data: any;
  timestamp: number;
}

export interface AlertEvent {
  stream_id: string;
  timestamp: number;
  alert_type: 'high_speed' | 'unusual_motion' | 'pose_anomaly' | 'system_error';
  severity: 'low' | 'medium' | 'high';
  message: string;
  metadata: Record<string, any>;
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T = any> {
  success: boolean;
  data: T[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

// UI Component Types
export interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'accent' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
  type?: 'button' | 'submit' | 'reset';
}

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

// Chart Data Types
export interface ChartDataPoint {
  timestamp: number;
  value: number;
  label?: string;
}

export interface AnalyticsChartData {
  speed: ChartDataPoint[];
  detections: ChartDataPoint[];
  motion_energy: ChartDataPoint[];
  processing_time: ChartDataPoint[];
}

// Error Types
export interface AppError {
  code: string;
  message: string;
  details?: any;
  timestamp: number;
}

// Form Types
export interface LoginForm {
  email: string;
  password: string;
}

export interface RegisterForm {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
}

export interface StreamCreateForm {
  title: string;
  description: string;
  enable_cv: boolean;
  enable_betting: boolean;
  quality: '720p' | '1080p' | '4K';
}

export interface BetPlaceForm {
  stream_id: string;
  bet_type: string;
  amount: number;
  prediction: any;
} 