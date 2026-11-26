"use client";

import { useRouter } from "next/navigation";
import React, { useEffect } from "react";

import { SiteHeader } from "@/components/site-header";
import { useAuth } from "@/hooks/use-auth";
import type { UserRole } from "@/types/auth";

export function getHomeRouteForRole(role: UserRole): string {
  if (role === "SUPER_ADMIN") return "/admin/dashboard";
  if (role === "AGENCY_OWNER" || role === "AGENCY_MANAGER" || role === "TRAVEL_AGENT") {
    return "/agency/dashboard";
  }
  return "/dashboard";
}

export function RoleGuard({
  allowedRoles,
  children,
}: {
  allowedRoles: UserRole[];
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { user, isLoading, isAuthenticated } = useAuth();

  const isAuthorized = user !== null && allowedRoles.includes(user.role);

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }
    if (user && !allowedRoles.includes(user.role)) {
      router.replace(getHomeRouteForRole(user.role));
    }
  }, [isLoading, isAuthenticated, user, allowedRoles, router]);

  if (isLoading || !isAuthorized) {
    return (
      <div className="min-h-screen flex flex-col">
        <SiteHeader />
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-12">
          <div className="h-40 animate-pulse rounded-xl bg-[var(--muted)]" />
        </main>
      </div>
    );
  }

  return <>{children}</>;
}
