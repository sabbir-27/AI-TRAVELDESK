"use client";

import {
  Activity,
  BarChart3,
  Bot,
  Building2,
  CreditCard,
  FileText,
  Inbox,
  KeyRound,
  LayoutDashboard,
  Menu,
  MessageSquare,
  Palette,
  Plane,
  Plug,
  Receipt,
  Settings,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

export interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const ADMIN_NAV: NavItem[] = [
  { label: "Dashboard", href: "/admin/dashboard", icon: LayoutDashboard },
  { label: "Agencies", href: "/admin/agencies", icon: Building2 },
  { label: "Users", href: "/admin/users", icon: Users },
  { label: "Subscriptions", href: "/admin/subscriptions", icon: CreditCard },
  { label: "Bookings", href: "/admin/bookings", icon: Plane },
  { label: "Flight Suppliers", href: "/admin/flight-suppliers", icon: Activity },
  { label: "Integrations", href: "/admin/integrations", icon: Plug },
  { label: "Analytics", href: "/admin/analytics", icon: BarChart3 },
  { label: "Billing", href: "/admin/billing", icon: Receipt },
  { label: "Settings", href: "/admin/settings", icon: Settings },
  { label: "Audit Logs", href: "/admin/audit-logs", icon: ShieldCheck },
];

const AGENCY_NAV: NavItem[] = [
  { label: "Dashboard", href: "/agency/dashboard", icon: LayoutDashboard },
  { label: "Bookings", href: "/agency/bookings", icon: Plane },
  { label: "Customers", href: "/agency/customers", icon: Users },
  { label: "Conversations", href: "/agency/conversations", icon: MessageSquare },
  { label: "AI Agents", href: "/agency/agents", icon: Bot },
  { label: "Integrations", href: "/agency/integrations", icon: Plug },
  { label: "Branding", href: "/agency/branding", icon: Palette },
  { label: "Analytics", href: "/agency/analytics", icon: BarChart3 },
  { label: "Billing", href: "/agency/billing", icon: Receipt },
  { label: "Team", href: "/agency/team", icon: KeyRound },
  { label: "Settings", href: "/agency/settings", icon: Settings },
  { label: "Agent Inbox", href: "/workspace/inbox", icon: Inbox },
];

const WORKSPACE_NAV: NavItem[] = [
  { label: "Inbox", href: "/workspace/inbox", icon: Inbox },
  { label: "Bookings", href: "/workspace/bookings", icon: Plane },
  { label: "Customers", href: "/workspace/customers", icon: Users },
  { label: "Agency Portal", href: "/agency/dashboard", icon: LayoutDashboard },
];

const CUSTOMER_NAV: NavItem[] = [
  { label: "My Workspace", href: "/dashboard", icon: LayoutDashboard },
  { label: "Book Flights", href: "/book", icon: Plane },
];

export function DashboardShell({
  portal,
  title,
  subtitle,
  children,
}: {
  portal: "admin" | "agency" | "workspace" | "customer";
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const navItems =
    portal === "admin"
      ? ADMIN_NAV
      : portal === "agency"
        ? AGENCY_NAV
        : portal === "workspace"
          ? WORKSPACE_NAV
          : CUSTOMER_NAV;

  const portalLabel =
    portal === "admin"
      ? "Platform Control"
      : portal === "agency"
        ? "Agency Portal"
        : portal === "workspace"
          ? "Agent Workspace"
          : "Traveler Portal";

  const sidebarLinks = (
    <nav aria-label={`${portalLabel} navigation`} className="space-y-1 px-3 py-4">
      {navItems.map((item) => {
        const Icon = item.icon;
        const active =
          pathname === item.href ||
          (item.href !== "/admin/dashboard" &&
            item.href !== "/agency/dashboard" &&
            item.href !== "/dashboard" &&
            pathname.startsWith(item.href));
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={() => setMobileOpen(false)}
            className={cn(
              "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-[var(--accent)] text-[var(--accent-foreground)]"
                : "text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );

  return (
    <div className="min-h-screen flex bg-[var(--background)] text-[var(--foreground)]">
      <aside className="hidden w-64 shrink-0 border-r border-[var(--border)] bg-[var(--surface)] lg:flex lg:flex-col">
        <div className="flex h-16 items-center gap-2.5 border-b border-[var(--border)] px-5">
          <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)] text-[var(--accent-foreground)]">
              <Plane className="h-4 w-4" />
            </span>
            <span>AI TravelDesk</span>
          </Link>
        </div>
        <div className="px-5 pt-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
            {portalLabel}
          </p>
        </div>
        <div className="flex-1 overflow-y-auto">{sidebarLinks}</div>
        <div className="border-t border-[var(--border)] p-4 text-xs text-[var(--muted-foreground)]">
          <Link href="/book" className="flex items-center gap-1.5 hover:text-[var(--foreground)]">
            <FileText className="h-3.5 w-3.5" />
            <span>Flight Booking Preview</span>
          </Link>
        </div>
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div
            className="fixed inset-0 bg-black/50"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <aside className="relative z-10 flex w-64 flex-col border-r border-[var(--border)] bg-[var(--surface)]">
            <div className="flex h-16 items-center justify-between border-b border-[var(--border)] px-4">
              <span className="font-semibold">AI TravelDesk</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setMobileOpen(false)}
                aria-label="Close navigation menu"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex-1 overflow-y-auto">{sidebarLinks}</div>
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-[var(--border)] bg-[var(--surface)]/90 px-4 backdrop-blur-md sm:px-6">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              className="lg:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation menu"
            >
              <Menu className="h-4 w-4" />
            </Button>
            <div>
              <h1 className="text-base font-semibold tracking-tight sm:text-lg">{title}</h1>
              {subtitle && (
                <p className="hidden text-xs text-[var(--muted-foreground)] sm:block">
                  {subtitle}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <ThemeToggle />
            {user && (
              <>
                <Badge variant="info" className="hidden sm:inline-flex">
                  {user.role}
                </Badge>
                <span className="hidden text-xs text-[var(--muted-foreground)] md:inline">
                  {user.email}
                </span>
                <Button variant="ghost" size="sm" onClick={() => void logout()}>
                  Sign out
                </Button>
              </>
            )}
          </div>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 space-y-6 px-4 py-6 sm:px-6">
          {children}
        </main>
      </div>
    </div>
  );
}
