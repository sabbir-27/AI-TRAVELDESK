import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdminDashboardPage from "@/app/admin/dashboard/page";
import { RoleGuard } from "@/components/role-guard";
import { AgencyRegisterForm } from "@/features/saas/agency-register-form";
import { saasService } from "@/services/saas-service";
import type { UserProfile } from "@/types/auth";

const pushMock = vi.fn();
const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    replace: replaceMock,
  }),
  usePathname: () => "/admin/dashboard",
}));

const authState: {
  user: UserProfile | null;
  isLoading: boolean;
  isAuthenticated: boolean;
} = {
  user: null,
  isLoading: false,
  isAuthenticated: false,
};

vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({
    ...authState,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
  }),
}));

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("Phase 2 Multi-Tenant SaaS UI & RBAC Protection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authState.user = null;
    authState.isLoading = false;
    authState.isAuthenticated = false;
  });

  it("validates required agency and owner fields in AgencyRegisterForm", async () => {
    renderWithQuery(<AgencyRegisterForm />);
    fireEvent.click(screen.getByRole("button", { name: /register agency/i }));

    expect(
      await screen.findByText(/agency name must be at least 2 characters/i)
    ).toBeInTheDocument();
    expect(
      await screen.findByText(/enter a valid agency contact email/i)
    ).toBeInTheDocument();
    expect(await screen.findByText(/owner full name is required/i)).toBeInTheDocument();
  });

  it("redirects unauthorized CUSTOMER away from SUPER_ADMIN routes", async () => {
    authState.user = {
      id: "u1",
      email: "cust@example.com",
      full_name: "Customer User",
      phone: null,
      role: "CUSTOMER",
      default_agency_id: null,
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString(),
    };
    authState.isAuthenticated = true;

    renderWithQuery(
      <RoleGuard allowedRoles={["SUPER_ADMIN"]}>
        <div>Secret Admin Area</div>
      </RoleGuard>
    );

    expect(screen.queryByText("Secret Admin Area")).not.toBeInTheDocument();
    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("renders Super Admin dashboard and approves pending agency", async () => {
    authState.user = {
      id: "admin-1",
      email: "admin@aitraveldesk.com",
      full_name: "Platform Owner",
      phone: null,
      role: "SUPER_ADMIN",
      default_agency_id: null,
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString(),
    };
    authState.isAuthenticated = true;

    vi.spyOn(saasService, "getAdminDashboard").mockResolvedValue({
      total_agencies: 1,
      active_agencies: 0,
      pending_agencies: 1,
      suspended_agencies: 0,
      total_users: 2,
      total_bookings: 0,
      active_subscriptions: 0,
      monthly_recurring_revenue_usd: "0.00",
      recent_agencies: [],
    });
    vi.spyOn(saasService, "listAdminAgencies").mockResolvedValue([
      {
        id: "ag-1",
        name: "Dhaka Sky Travels",
        slug: "dhaka-sky",
        status: "PENDING",
        contact_email: "ops@dhakasky.com",
        contact_phone: null,
        website_url: null,
        country_code: "BD",
        default_currency: "USD",
        logo_url: null,
        primary_color: "#0F172A",
        secondary_color: "#2563EB",
        service_fee_flat: "0.00",
        service_fee_percent: "0.00",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);
    vi.spyOn(saasService, "listPublicPlans").mockResolvedValue([]);
    const approveSpy = vi.spyOn(saasService, "approveAgency").mockResolvedValue({
      id: "ag-1",
      name: "Dhaka Sky Travels",
      slug: "dhaka-sky",
      status: "ACTIVE",
      contact_email: "ops@dhakasky.com",
      contact_phone: null,
      website_url: null,
      country_code: "BD",
      default_currency: "USD",
      logo_url: null,
      primary_color: "#0F172A",
      secondary_color: "#2563EB",
      service_fee_flat: "0.00",
      service_fee_percent: "0.00",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    renderWithQuery(<AdminDashboardPage />);

    expect(await screen.findByText("Dhaka Sky Travels")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /approve/i }));

    await waitFor(() => {
      expect(approveSpy).toHaveBeenCalledWith("ag-1", "Approved by Super Admin");
    });
  });
});
