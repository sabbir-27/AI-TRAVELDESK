import { apiRequest, tokenStorage } from "@/lib/api-client";
import type {
  LoginPayload,
  RegisterPayload,
  TokenPairResponse,
  UserProfile,
} from "@/types/auth";

export const authService = {
  async register(payload: RegisterPayload): Promise<TokenPairResponse> {
    const res = await apiRequest<TokenPairResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
      skipAuth: true,
    });
    tokenStorage.setTokens(res.access_token, res.refresh_token);
    return res;
  },

  async login(payload: LoginPayload): Promise<TokenPairResponse> {
    const res = await apiRequest<TokenPairResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
      skipAuth: true,
    });
    tokenStorage.setTokens(res.access_token, res.refresh_token);
    return res;
  },

  async logout(): Promise<void> {
    const refreshToken = tokenStorage.getRefreshToken();
    try {
      await apiRequest<{ message: string }>("/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } finally {
      tokenStorage.clearTokens();
    }
  },

  async getMe(): Promise<UserProfile> {
    return apiRequest<UserProfile>("/auth/me", { method: "GET" });
  },
};
