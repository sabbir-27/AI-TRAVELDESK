import type { TokenPairResponse, UserRole } from "@/types/auth";

export type AgencyStatus = "PENDING" | "ACTIVE" | "SUSPENDED";
export type SubscriptionTier = "STARTER" | "PROFESSIONAL" | "BUSINESS" | "ENTERPRISE";
export type SubscriptionStatus = "TRIALING" | "ACTIVE" | "PAST_DUE" | "CANCELLED";
export type BillingCycle = "MONTHLY" | "ANNUAL";

export interface Agency {
  id: string;
  name: string;
  slug: string;
  status: AgencyStatus;
  contact_email: string;
  contact_phone: string | null;
  website_url: string | null;
  country_code: string;
  default_currency: string;
  logo_url: string | null;
  primary_color: string;
  secondary_color: string;
  service_fee_flat: string;
  service_fee_percent: string;
  created_at: string;
  updated_at: string;
}

export interface SubscriptionPlan {
  id: string;
  tier: SubscriptionTier;
  name: string;
  monthly_price_usd: string;
  annual_price_usd: string;
  monthly_api_limit: number;
  monthly_conversation_limit: number;
  monthly_booking_limit: number;
  overage_per_booking_usd: string;
  features: Record<string, unknown>;
  is_active: boolean;
}

export interface Subscription {
  id: string;
  agency_id: string;
  plan_id: string;
  status: SubscriptionStatus;
  billing_cycle: BillingCycle;
  current_period_start: string;
  current_period_end: string;
  api_requests_used: number;
  conversations_used: number;
  bookings_used: number;
  plan: SubscriptionPlan | null;
}

export interface Invoice {
  id: string;
  agency_id: string;
  subscription_id: string | null;
  invoice_number: string;
  amount_usd: string;
  currency: string;
  status: string;
  due_at: string;
  paid_at: string | null;
  line_items: Record<string, unknown>;
  created_at: string;
}

export interface TeamMember {
  id: string;
  user_id: string;
  agency_id: string;
  email: string;
  full_name: string;
  phone: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface AdminDashboardStats {
  total_agencies: number;
  active_agencies: number;
  pending_agencies: number;
  suspended_agencies: number;
  total_users: number;
  total_bookings: number;
  active_subscriptions: number;
  monthly_recurring_revenue_usd: string;
  recent_agencies: Agency[];
}

export interface AgencyDashboardStats {
  agency: Agency;
  team_member_count: number;
  customer_count: number;
  booking_count: number;
  conversation_count: number;
  subscription: Subscription | null;
}

export interface AgencyRegisterPayload {
  owner_full_name: string;
  owner_email: string;
  owner_password: string;
  owner_phone?: string;
  agency_name: string;
  slug?: string;
  contact_email: string;
  contact_phone?: string;
  website_url?: string;
  country_code: string;
  default_currency: string;
  plan_tier: SubscriptionTier;
  billing_cycle: BillingCycle;
}

export interface AgencyRegisterResponse {
  agency: Agency;
  tokens: TokenPairResponse;
}

export interface AgencyProfileUpdatePayload {
  name?: string;
  contact_email?: string;
  primary_color?: string;
  secondary_color?: string;
  service_fee_flat?: number;
  service_fee_percent?: number;
}

export interface TeamMemberCreatePayload {
  full_name: string;
  email: string;
  password: string;
  phone?: string;
  role: "AGENCY_MANAGER" | "TRAVEL_AGENT";
}

export interface CustomerRecord {
  id: string;
  agency_id: string;
  email: string;
  full_name: string;
  phone: string | null;
  preferred_language: string;
  created_at: string;
}

export interface CustomerCreatePayload {
  email: string;
  full_name: string;
  phone?: string;
  preferred_language?: string;
}

export interface BookingSummary {
  id: string;
  agency_id: string;
  customer_id: string;
  booking_reference: string;
  pnr: string | null;
  status: string;
  currency: string;
  total_amount: string;
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  agency_id: string;
  customer_id: string | null;
  channel: string;
  status: string;
  detected_language: string;
  created_at: string;
}

export interface AdminAgencyDetail {
  agency: Agency;
  member_count: number;
  customer_count: number;
  booking_count: number;
  subscription: Subscription | null;
}

export interface AdminSubscriptionRow {
  subscription: Subscription;
  agency_name: string;
  agency_slug: string;
}

export interface AdminAuditLog {
  id: string;
  agency_id: string | null;
  actor_user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  ip_address: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface AgentConfig {
  id: string;
  agency_id: string;
  agent_name: string;
  welcome_message: string;
  supported_languages: string[];
  tone: string;
  auto_handoff_threshold: number;
  custom_instructions: string | null;
  is_active: boolean;
}

export interface AgentConfigUpdatePayload {
  agent_name?: string;
  welcome_message?: string;
  supported_languages?: string[];
  tone?: string;
  auto_handoff_threshold?: number;
  custom_instructions?: string;
  is_active?: boolean;
}

export interface AgentMessage {
  id: string;
  conversation_id: string;
  sender_type: "CUSTOMER" | "AI_AGENT" | "HUMAN_AGENT" | "SYSTEM";
  sender_user_id: string | null;
  content: string;
  is_internal_note: boolean;
  tool_metadata: Record<string, unknown>;
  created_at: string;
}

export interface AgentConversationDetail {
  id: string;
  agency_id: string;
  customer_id: string | null;
  channel: string;
  status: string;
  detected_language: string;
  thread_state: Record<string, unknown>;
  messages: AgentMessage[];
  created_at: string;
  updated_at: string;
}

export interface AgentTurnResponse {
  conversation_id: string;
  status: string;
  detected_language: string;
  intent: string;
  active_agent: string;
  booking_state?: Record<string, unknown>;
  travel_plan?: Record<string, unknown>;
  missing_slots: string[];
  flight_offers: Record<string, unknown>[];
  comparison_matrix: Record<string, unknown>[];
  fare_rules_summary: Record<string, unknown> | null;
  booking_summary: Record<string, unknown> | null;
  booking_record?: Record<string, unknown> | null;
  requires_human_handoff: boolean;
  llm_provider?: string | null;
  tool_events: Record<string, unknown>[];
  customer_message: AgentMessage;
  agent_message: AgentMessage;
}

export interface FlightOfferDto {
  id: string;
  agency_id: string;
  supplier: string;
  supplier_offer_id: string;
  origin: string;
  destination: string;
  departure_at: string;
  currency: string;
  base_fare: string;
  taxes: string;
  total_fare: string;
  expires_at: string;
  is_sandbox: boolean;
  airline: string | null;
  flight_number: string | null;
  duration_minutes: number | null;
  stops: number | null;
  baggage: string | null;
  refundable: boolean | null;
}

export interface FlightSearchPayload {
  origin: string;
  destination: string;
  departure_date: string;
  return_date?: string;
  trip_type: "one-way" | "round-trip" | "multi-city";
  adults: number;
  cabin_class: string;
}

export interface BookingCreatedDto {
  id: string;
  booking_reference: string;
  pnr: string | null;
  supplier: string | null;
  status: string;
  currency: string;
  supplier_amount: string;
  service_fee_amount: string;
  total_amount: string;
  is_sandbox: boolean;
}

export interface IntegrationCredentialSummary {
  id: string;
  key_prefix: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AgencyIntegrationDto {
  id: string;
  agency_id: string;
  integration_type: "WIDGET" | "REST_API" | "FLIGHT_SUPPLIER" | "PAYMENT_GATEWAY" | "NOTIFICATION";
  provider_name: string;
  is_enabled: boolean;
  allowed_origins: string[];
  config: Record<string, unknown>;
  credentials: IntegrationCredentialSummary[];
}

export interface WidgetTokenIssuedDto {
  agency_id: string;
  widget_token: string;
  allowed_origins: string[];
  embed_snippet: string;
}

export interface ApiKeyIssuedDto {
  credential_id: string;
  label: string;
  key_prefix: string;
  api_key: string;
  created_at: string;
}

export interface PaymentDto {
  id: string;
  booking_id: string;
  gateway: string;
  gateway_transaction_id: string | null;
  status: string;
  amount: string;
  currency: string;
  verified_at: string | null;
  checkout_url: string | null;
  is_sandbox: boolean;
}

export interface TicketDto {
  id: string;
  booking_id: string;
  passenger_id: string;
  e_ticket_number: string | null;
  status: string;
  issued_at: string | null;
}

export interface TicketingOutcomeDto {
  booking_id: string;
  booking_status: string;
  tickets: TicketDto[];
  recovery_ticket_id: string | null;
  message: string;
}

export interface WorkspaceInboxItem {
  id: string;
  channel: string;
  status: string;
  detected_language: string;
  customer_name: string | null;
  customer_email: string | null;
  assigned_to_user_id: string | null;
  assigned_to_name: string | null;
  last_message_preview: string | null;
  updated_at: string;
}

export interface SupportTicketDto {
  id: string;
  agency_id: string;
  conversation_id: string | null;
  booking_id: string | null;
  assigned_to_user_id: string | null;
  subject: string;
  priority: "LOW" | "MEDIUM" | "HIGH" | "URGENT";
  status: "OPEN" | "IN_PROGRESS" | "WAITING_CUSTOMER" | "RESOLVED" | "CLOSED";
  created_at: string;
  updated_at: string;
}

export interface WorkspaceConversationDetailDto {
  id: string;
  agency_id: string;
  channel: string;
  status: string;
  detected_language: string;
  thread_state: Record<string, unknown>;
  customer: CustomerRecord | null;
  bookings: BookingSummary[];
  active_assignment: {
    id: string;
    assigned_to_user_id: string;
    reason: string | null;
  } | null;
  support_tickets: SupportTicketDto[];
  messages: AgentMessage[];
  created_at: string;
  updated_at: string;
}

export interface AiSuggestionDto {
  conversation_id: string;
  detected_language: string;
  intent: string;
  suggestions: string[];
}
