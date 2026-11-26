import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BookFlightsPage from "@/app/book/page";
import ContactPage from "@/app/contact/page";
import HomePage from "@/app/page";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { ToastProvider } from "@/components/ui/toast";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
  usePathname: () => "/admin/dashboard",
}));

vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({
    user: {
      id: "u-admin",
      email: "admin@aitraveldesk.com",
      full_name: "Platform Owner",
      phone: null,
      role: "SUPER_ADMIN",
      default_agency_id: null,
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString(),
    },
    isLoading: false,
    isAuthenticated: true,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
  }),
}));

function renderPage(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>{ui}</ToastProvider>
    </QueryClientProvider>
  );
}

describe("Phase 3 Frontend Experience", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders landing page demonstration tabs and pricing", () => {
    renderPage(<HomePage />);
    expect(
      screen.getByText(/automate flight search, booking, and support/i)
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Widget" }));
    expect(screen.getByText(/data-agency-id=/i)).toBeInTheDocument();
  });

  it("supports flight filtering, comparison, and passenger validation on /book", async () => {
    renderPage(<BookFlightsPage />);

    // Filter to Emirates only
    fireEvent.click(screen.getByLabelText("Emirates"));
    expect(screen.getByText("EK-583")).toBeInTheDocument();
    expect(screen.queryByText("QR-639")).not.toBeInTheDocument();

    // Select offer and submit empty passenger form to trigger Zod validation
    fireEvent.click(screen.getByRole("button", { name: /^select$/i }));
    fireEvent.click(screen.getByRole("button", { name: /validate passenger/i }));

    expect(await screen.findByText(/first name is required/i)).toBeInTheDocument();
    expect(await screen.findByText(/passport number must be at least 6/i)).toBeInTheDocument();
  });

  it("renders admin navigation items in DashboardShell", () => {
    renderPage(
      <DashboardShell portal="admin" title="Control Plane">
        <div>Inner Content</div>
      </DashboardShell>
    );
    expect(screen.getByRole("link", { name: "Agencies" })).toHaveAttribute(
      "href",
      "/admin/agencies"
    );
    expect(screen.getByRole("link", { name: "Audit Logs" })).toHaveAttribute(
      "href",
      "/admin/audit-logs"
    );
  });

  it("validates contact form inputs", async () => {
    renderPage(<ContactPage />);
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));
    expect(await screen.findByText(/^name is required$/i)).toBeInTheDocument();
    expect(await screen.findByText(/enter a valid email address/i)).toBeInTheDocument();
  });
});
