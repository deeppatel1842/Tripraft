// Purpose: Provides index logic and exports for packages\types\src.
/** UUIDs remain strings at application and API boundaries. */
export type UUID = string;
export type Money = number;
export interface ApiEnvelope<T> {
  success: boolean;
  data: T | null;
  message?: string;
  error?: { code: string; message: string; details?: unknown };
  meta?: { request_id?: string; timestamp?: string; pagination?: unknown };
}
export interface AuthUser {
  id: UUID;
  email: string;
  display_name?: string | null;
  is_admin: boolean;
}
export interface HealthStatus {
  status: string;
  service?: string;
  version?: string;
  timestamp: string;
  checks?: Record<string, { status: string; note?: string; error?: string }>;
}
