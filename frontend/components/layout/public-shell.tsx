"use client";

import { Menu, Plane, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useState } from "react";

import { getHomeRouteForRole } from "@/components/role-guard";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

const PUBLIC_LINKS = [
  { label: "Features", href: "/features" },
  { label: "Solutions", href: "/solutions" },
  { label: "Pricing", href: "/pricing" },
  { label: "Integrations", href: "/integrations" },
  { label: "Book Flights", href: "/book" },
  { label: "About", href: "/about" },
  { label: "Contact", href: "/contact" },
];

export function PublicShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { isAuthenticated, user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col bg-[var(--background)] text-[var(--foreground)]">
      <header className="sticky top-0 z-30 border-b border-[var(--border)] bg-[var(--surface)]/90 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2.5 font-semibold tracking-tight">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)] text-[var(--accent-foreground)]">
              <Plane className="h-4 w-4" />
            </span>
            <span>AI TravelDesk</span>
          </Link>

          <nav aria-label="Main navigation" className="hidden items-center gap-1 lg:flex">
            {PUBLIC_LINKS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                  pathname === item.href
                    ? "bg-[var(--muted)] text-[var(--foreground)]"
                    : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-2">
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
                <Link href="/register-agency" className="hidden sm:inline-flex">
                  <Button variant="ghost" size="sm">
                    For Agencies
                  </Button>
                </Link>
                <Link href="/login" className="hidden sm:inline-flex">
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
            <Button
              variant="ghost"
              size="sm"
              className="lg:hidden"
              onClick={() => setMenuOpen((prev) => !prev)}
              aria-label="Toggle menu"
            >
              {menuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </Button>
          </div>
        </div>

        {menuOpen && (
          <div className="border-t border-[var(--border)] bg-[var(--surface)] px-4 py-3 lg:hidden">
            <div className="flex flex-col space-y-1">
              {PUBLIC_LINKS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMenuOpen(false)}
                  className="rounded-lg px-3 py-2 text-sm font-medium text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
                >
                  {item.label}
                </Link>
              ))}
              {!isAuthenticated && (
                <div className="flex gap-2 pt-2">
                  <Link href="/register-agency" className="flex-1">
                    <Button variant="secondary" size="sm" className="w-full">
                      For Agencies
                    </Button>
                  </Link>
                  <Link href="/login" className="flex-1">
                    <Button variant="ghost" size="sm" className="w-full">
                      Sign in
                    </Button>
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-[var(--border)] bg-[var(--surface)]">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 py-12 sm:grid-cols-2 sm:px-6 lg:grid-cols-4">
          <div className="space-y-3">
            <div className="flex items-center gap-2 font-semibold">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--accent)] text-[var(--accent-foreground)]">
                <Plane className="h-3.5 w-3.5" />
              </span>
              <span>AI TravelDesk</span>
            </div>
            <p className="text-xs leading-relaxed text-[var(--muted-foreground)]">
              Multi-tenant B2B SaaS &amp; AI flight-booking operating platform for independent
              travel agencies.
            </p>
          </div>

          <div className="space-y-2 text-xs">
            <p className="font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
              Platform
            </p>
            <ul className="space-y-1.5">
              <li>
                <Link href="/features" className="hover:underline">
                  AI Flight Agent
                </Link>
              </li>
              <li>
                <Link href="/solutions" className="hover:underline">
                  Agency Solutions
                </Link>
              </li>
              <li>
                <Link href="/integrations" className="hover:underline">
                  Widget &amp; REST API
                </Link>
              </li>
              <li>
                <Link href="/pricing" className="hover:underline">
                  Pricing Plans
                </Link>
              </li>
            </ul>
          </div>

          <div className="space-y-2 text-xs">
            <p className="font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
              Workspaces
            </p>
            <ul className="space-y-1.5">
              <li>
                <Link href="/register-agency" className="hover:underline">
                  Agency Onboarding
                </Link>
              </li>
              <li>
                <Link href="/book" className="hover:underline">
                  Flight Booking UI
                </Link>
              </li>
              <li>
                <Link href="/login" className="hover:underline">
                  Portal Sign In
                </Link>
              </li>
            </ul>
          </div>

          <div className="space-y-2 text-xs">
            <p className="font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
              Company
            </p>
            <ul className="space-y-1.5">
              <li>
                <Link href="/about" className="hover:underline">
                  About Us
                </Link>
              </li>
              <li>
                <Link href="/contact" className="hover:underline">
                  Contact Sales
                </Link>
              </li>
            </ul>
          </div>
        </div>
        <div className="border-t border-[var(--border)] py-4 text-center text-xs text-[var(--muted-foreground)]">
          © {new Date().getFullYear()} AI TravelDesk. Multi-Tenant B2B Travel Technology Platform.
        </div>
      </footer>
    </div>
  );
}
