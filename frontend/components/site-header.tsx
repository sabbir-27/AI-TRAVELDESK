"use client";

import { Plane } from "lucide-react";
import Link from "next/link";

import { getHomeRouteForRole } from "@/components/role-guard";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { useAuth } from "@/hooks/use-auth";

export function SiteHeader() {
  const { isAuthenticated, user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-30 border-b border-[var(--border)] bg-[var(--surface)]/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5 font-semibold tracking-tight">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)] text-[var(--accent-foreground)]">
            <Plane className="h-4 w-4" />
          </span>
          <span>AI TravelDesk</span>
        </Link>

        <nav className="flex items-center gap-2 sm:gap-3">
          <ThemeToggle />
          {isAuthenticated && user ? (
            <>
              <Link href={getHomeRouteForRole(user.role)}>
                <Button variant="secondary" size="sm">
                  Dashboard
                </Button>
              </Link>
              <Button variant="ghost" size="sm" onClick={() => void logout()}>
                Sign out
              </Button>
            </>
          ) : (
            <>
              <Link href="/register-agency">
                <Button variant="ghost" size="sm">
                  For Agencies
                </Button>
              </Link>
              <Link href="/login">
                <Button variant="ghost" size="sm">
                  Sign in
                </Button>
              </Link>
              <Link href="/register">
                <Button variant="primary" size="sm">
                  Get started
                </Button>
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
