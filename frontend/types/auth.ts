export type UserRole =
  | "SUPER_ADMIN"
  | "AGENCY_OWNER"
  | "AGENCY_MANAGER"
  | "TRAVEL_AGENT"
  | "CUSTOMER";

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  role: UserRole;
  default_agency_id: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface TokenPairResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserProfile;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
}
