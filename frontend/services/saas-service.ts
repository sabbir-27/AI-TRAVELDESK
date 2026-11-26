import { apiRequest, tokenStorage } from "@/lib/api-client";
import type { UserProfile } from "@/types/auth";
import type {
  AdminAgencyDetail,
  AdminAuditLog,
  AdminDashboardStats,
  AdminSubscriptionRow,
  Agency,
  AgencyDashboardStats,
  AgencyIntegrationDto,
  AgencyProfileUpdatePayload,
  AgencyRegisterPayload,
  AgencyRegisterResponse,
  AgentConfig,
  AgentConfigUpdatePayload,
  AgentConversationDetail,
  AgentMessage,
  AgentTurnResponse,
  AiSuggestionDto,
  ApiKeyIssuedDto,
  BillingCycle,
  BookingCreatedDto,
  BookingSummary,
  ConversationSummary,
  CustomerCreatePayload,
  CustomerRecord,
  FlightOfferDto,
  FlightSearchPayload,
  Invoice,
  PaymentDto,
  Subscription,
  SubscriptionPlan,
  SubscriptionTier,
  SupportTicketDto,
  TeamMember,
  TeamMemberCreatePayload,
  TicketDto,
  TicketingOutcomeDto,
  WidgetTokenIssuedDto,
  WorkspaceConversationDetailDto,
  WorkspaceInboxItem,
} from "@/types/saas";

export const saasService = {
  async listPublicPlans(): Promise<SubscriptionPlan[]> {
    return apiRequest<SubscriptionPlan[]>("/agencies/plans", {
      method: "GET",
      skipAuth: true,
    });
  },

  async registerAgency(payload: AgencyRegisterPayload): Promise<AgencyRegisterResponse> {
    const res = await apiRequest<AgencyRegisterResponse>("/agencies/register", {
      method: "POST",
      body: JSON.stringify(payload),
      skipAuth: true,
    });
    tokenStorage.setTokens(res.tokens.access_token, res.tokens.refresh_token);
    return res;
  },

  // Super Admin endpoints
  async getAdminDashboard(): Promise<AdminDashboardStats> {
    return apiRequest<AdminDashboardStats>("/admin/dashboard", { method: "GET" });
  },

  async listAdminAgencies(status?: string): Promise<Agency[]> {
    const query = status ? `?status=${encodeURIComponent(status)}` : "";
    return apiRequest<Agency[]>(`/admin/agencies${query}`, { method: "GET" });
  },

  async approveAgency(agencyId: string, reason?: string): Promise<Agency> {
    return apiRequest<Agency>(`/admin/agencies/${agencyId}/approve`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  },

  async suspendAgency(agencyId: string, reason?: string): Promise<Agency> {
    return apiRequest<Agency>(`/admin/agencies/${agencyId}/suspend`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  },

  // Agency tenant endpoints
  async getAgencyDashboard(): Promise<AgencyDashboardStats> {
    return apiRequest<AgencyDashboardStats>("/agency/dashboard", { method: "GET" });
  },

  async updateAgencyProfile(payload: AgencyProfileUpdatePayload): Promise<Agency> {
    return apiRequest<Agency>("/agency/profile", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  async listTeamMembers(): Promise<TeamMember[]> {
    return apiRequest<TeamMember[]>("/agency/team", { method: "GET" });
  },

  async addTeamMember(payload: TeamMemberCreatePayload): Promise<TeamMember> {
    return apiRequest<TeamMember>("/agency/team", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async listInvoices(): Promise<Invoice[]> {
    return apiRequest<Invoice[]>("/agency/invoices", { method: "GET" });
  },

  async changeSubscriptionPlan(
    plan_tier: SubscriptionTier,
    billing_cycle: BillingCycle
  ): Promise<Subscription> {
    return apiRequest<Subscription>("/agency/subscription/change-plan", {
      method: "POST",
      body: JSON.stringify({ plan_tier, billing_cycle }),
    });
  },

  async getAdminAgencyDetail(agencyId: string): Promise<AdminAgencyDetail> {
    return apiRequest<AdminAgencyDetail>(`/admin/agencies/${agencyId}`, { method: "GET" });
  },

  async listAdminUsers(): Promise<UserProfile[]> {
    return apiRequest<UserProfile[]>("/admin/users", { method: "GET" });
  },

  async listAdminSubscriptions(): Promise<AdminSubscriptionRow[]> {
    return apiRequest<AdminSubscriptionRow[]>("/admin/subscriptions", { method: "GET" });
  },

  async listAdminBookings(): Promise<BookingSummary[]> {
    return apiRequest<BookingSummary[]>("/admin/bookings", { method: "GET" });
  },

  async listAdminAuditLogs(): Promise<AdminAuditLog[]> {
    return apiRequest<AdminAuditLog[]>("/admin/audit-logs", { method: "GET" });
  },

  async listAgencyCustomers(): Promise<CustomerRecord[]> {
    return apiRequest<CustomerRecord[]>("/agency/customers", { method: "GET" });
  },

  async createAgencyCustomer(payload: CustomerCreatePayload): Promise<CustomerRecord> {
    return apiRequest<CustomerRecord>("/agency/customers", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async listAgencyBookings(): Promise<BookingSummary[]> {
    return apiRequest<BookingSummary[]>("/agency/bookings", { method: "GET" });
  },

  async listAgencyConversations(): Promise<ConversationSummary[]> {
    return apiRequest<ConversationSummary[]>("/agency/conversations", { method: "GET" });
  },

  async getAgentConfig(): Promise<AgentConfig> {
    return apiRequest<AgentConfig>("/agency/agent-config", { method: "GET" });
  },

  async updateAgentConfig(payload: AgentConfigUpdatePayload): Promise<AgentConfig> {
    return apiRequest<AgentConfig>("/agency/agent-config", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  async createAgentConversation(channel = "WEB"): Promise<AgentConversationDetail> {
    return apiRequest<AgentConversationDetail>("/agent/conversations", {
      method: "POST",
      body: JSON.stringify({ channel }),
    });
  },

  async sendAgentMessage(
    conversationId: string,
    content: string
  ): Promise<AgentTurnResponse> {
    return apiRequest<AgentTurnResponse>(`/agent/conversations/${conversationId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
  },

  async getAgentConversation(conversationId: string): Promise<AgentConversationDetail> {
    return apiRequest<AgentConversationDetail>(`/agent/conversations/${conversationId}`, {
      method: "GET",
    });
  },

  async searchFlights(payload: FlightSearchPayload): Promise<FlightOfferDto[]> {
    return apiRequest<FlightOfferDto[]>("/flights/search", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async priceFlightOffer(offerId: string): Promise<{
    offer: FlightOfferDto;
    price_changed: boolean;
    previous_total_fare: string;
    fare_rules: Record<string, unknown>;
  }> {
    return apiRequest("/flights/price", {
      method: "POST",
      body: JSON.stringify({ offer_id: offerId }),
    });
  },

  async createReservation(payload: {
    offer_id: string;
    customer_email: string;
    customer_name: string;
    customer_phone?: string;
    passengers: Array<{
      first_name: string;
      last_name: string;
      date_of_birth: string;
      nationality: string;
      passport_number?: string;
      email?: string;
      phone?: string;
    }>;
    idempotency_key: string;
    approved: boolean;
  }): Promise<BookingCreatedDto> {
    return apiRequest<BookingCreatedDto>("/bookings", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async listAgencyIntegrations(): Promise<AgencyIntegrationDto[]> {
    return apiRequest<AgencyIntegrationDto[]>("/agency/integrations", { method: "GET" });
  },

  async issueWidgetToken(allowed_origins?: string[]): Promise<WidgetTokenIssuedDto> {
    return apiRequest<WidgetTokenIssuedDto>("/agency/integrations/widget/token", {
      method: "POST",
      body: JSON.stringify({ allowed_origins: allowed_origins ?? [] }),
    });
  },

  async updateWidgetOrigins(allowed_origins: string[]): Promise<string[]> {
    return apiRequest<string[]>("/agency/integrations/widget/origins", {
      method: "PATCH",
      body: JSON.stringify({ allowed_origins }),
    });
  },

  async createApiKey(label: string): Promise<ApiKeyIssuedDto> {
    return apiRequest<ApiKeyIssuedDto>("/agency/integrations/api-keys", {
      method: "POST",
      body: JSON.stringify({ label }),
    });
  },

  async revokeApiKey(credentialId: string): Promise<void> {
    await apiRequest(`/agency/integrations/api-keys/${credentialId}`, {
      method: "DELETE",
    });
  },

  async initiatePayment(payload: {
    booking_id: string;
    gateway: "sslcommerz" | "bkash" | "nagad" | "stripe" | "sandbox";
    idempotency_key: string;
  }): Promise<PaymentDto> {
    return apiRequest<PaymentDto>("/payments/initiate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async verifyPayment(paymentId: string): Promise<PaymentDto> {
    return apiRequest<PaymentDto>(`/payments/${paymentId}/verify`, {
      method: "POST",
    });
  },

  async issueBookingTickets(bookingId: string): Promise<TicketingOutcomeDto> {
    return apiRequest<TicketingOutcomeDto>(`/bookings/${bookingId}/issue-ticket`, {
      method: "POST",
      body: JSON.stringify({ simulate_failure: false }),
    });
  },

  async listBookingTickets(bookingId: string): Promise<TicketDto[]> {
    return apiRequest<TicketDto[]>(`/bookings/${bookingId}/tickets`, { method: "GET" });
  },

  async cancelBooking(bookingId: string, reason: string): Promise<{ booking_status: string }> {
    return apiRequest(`/bookings/${bookingId}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason, confirm: true }),
    });
  },

  async refundBooking(bookingId: string, reason?: string): Promise<{ amount: string; booking_status: string }> {
    return apiRequest(`/bookings/${bookingId}/refund`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  },

  async getWorkspaceInbox(status?: string): Promise<WorkspaceInboxItem[]> {
    const q = status ? `?status=${encodeURIComponent(status)}` : "";
    return apiRequest<WorkspaceInboxItem[]>(`/workspace/inbox${q}`, { method: "GET" });
  },

  async getWorkspaceConversation(
    conversationId: string
  ): Promise<WorkspaceConversationDetailDto> {
    return apiRequest<WorkspaceConversationDetailDto>(
      `/workspace/conversations/${conversationId}`,
      { method: "GET" }
    );
  },

  async assignWorkspaceConversation(
    conversationId: string,
    assigned_to_user_id: string,
    reason?: string
  ): Promise<void> {
    await apiRequest(`/workspace/conversations/${conversationId}/assign`, {
      method: "POST",
      body: JSON.stringify({ assigned_to_user_id, reason }),
    });
  },

  async takeoverWorkspaceConversation(
    conversationId: string,
    action: "takeover" | "release" | "resolve",
    reason?: string
  ): Promise<WorkspaceConversationDetailDto> {
    return apiRequest<WorkspaceConversationDetailDto>(
      `/workspace/conversations/${conversationId}/takeover`,
      {
        method: "POST",
        body: JSON.stringify({ action, reason }),
      }
    );
  },

  async replyWorkspaceConversation(
    conversationId: string,
    content: string,
    is_internal_note = false
  ): Promise<AgentMessage> {
    return apiRequest<AgentMessage>(`/workspace/conversations/${conversationId}/reply`, {
      method: "POST",
      body: JSON.stringify({ content, is_internal_note }),
    });
  },

  async getWorkspaceSuggestions(conversationId: string): Promise<AiSuggestionDto> {
    return apiRequest<AiSuggestionDto>(
      `/workspace/conversations/${conversationId}/suggestions`,
      { method: "GET" }
    );
  },

  async listSupportTickets(): Promise<SupportTicketDto[]> {
    return apiRequest<SupportTicketDto[]>("/workspace/support-tickets", { method: "GET" });
  },

  async createSupportTicket(payload: {
    subject: string;
    priority: "LOW" | "MEDIUM" | "HIGH" | "URGENT";
    conversation_id?: string;
    booking_id?: string;
  }): Promise<SupportTicketDto> {
    return apiRequest<SupportTicketDto>("/workspace/support-tickets", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async updateSupportTicket(
    ticketId: string,
    payload: {
      status?: "OPEN" | "IN_PROGRESS" | "WAITING_CUSTOMER" | "RESOLVED" | "CLOSED";
    }
  ): Promise<SupportTicketDto> {
    return apiRequest<SupportTicketDto>(`/workspace/support-tickets/${ticketId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
};
