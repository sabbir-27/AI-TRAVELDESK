import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "@/app/dashboard/page";
import { Providers } from "@/components/providers";
import { LoginForm, RegisterForm } from "@/features/auth/auth-forms";

const pushMock = vi.fn();
const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    replace: replaceMock,
  }),
  usePathname: () => "/login",
}));

describe("Phase 1 Frontend Auth & Route Protection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it("validates email and password fields on LoginForm", async () => {
    render(
      <Providers>
        <LoginForm />
      </Providers>
    );

    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText(/enter a valid email address/i)).toBeInTheDocument();
    expect(await screen.findByText(/password is required/i)).toBeInTheDocument();
  });

  it("validates registration fields on RegisterForm", async () => {
    render(
      <Providers>
        <RegisterForm />
      </Providers>
    );

    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    expect(
      await screen.findByText(/full name must be at least 2 characters/i)
    ).toBeInTheDocument();
    expect(await screen.findByText(/enter a valid email address/i)).toBeInTheDocument();
    expect(
      await screen.findByText(/password must be at least 8 characters/i)
    ).toBeInTheDocument();
  });

  it("redirects unauthenticated users away from protected /dashboard", async () => {
    render(
      <Providers>
        <DashboardPage />
      </Providers>
    );

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/login");
    });
  });
});
