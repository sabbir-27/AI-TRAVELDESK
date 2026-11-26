"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Bot, CreditCard, Users } from "lucide-react";
import Link from "next/link";
import React, { useState } from "react";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api-client";
import { saasService } from "@/services/saas-service";
import type { BillingCycle, SubscriptionTier } from "@/types/saas";

function AgencyDashboardContent() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const isOwner = user?.role === "AGENCY_OWNER";
  const canViewTeam = user?.role === "AGENCY_OWNER" || user?.role === "AGENCY_MANAGER";

  const [memberName, setMemberName] = useState("");
  const [memberEmail, setMemberEmail] = useState("");
  const [memberPassword, setMemberPassword] = useState("");
  const [memberRole, setMemberRole] = useState<"TRAVEL_AGENT" | "AGENCY_MANAGER">(
    "TRAVEL_AGENT"
  );
  const [selectedTier, setSelectedTier] = useState<SubscriptionTier>("PROFESSIONAL");
  const [selectedCycle, setSelectedCycle] = useState<BillingCycle>("MONTHLY");

  const dashboardQuery = useQuery({
    queryKey: ["agency", "dashboard"],
    queryFn: () => saasService.getAgencyDashboard(),
  });

  const teamQuery = useQuery({
    queryKey: ["agency", "team"],
    queryFn: () => saasService.listTeamMembers(),
    enabled: canViewTeam,
  });

  const invoicesQuery = useQuery({
    queryKey: ["agency", "invoices"],
    queryFn: () => saasService.listInvoices(),
    enabled: isOwner,
  });

  const addMemberMutation = useMutation({
    mutationFn: () =>
      saasService.addTeamMember({
        full_name: memberName,
        email: memberEmail,
        password: memberPassword,
        role: memberRole,
      }),
    onSuccess: (member) => {
      pushToast({ variant: "success", title: `Added ${member.full_name}` });
      setMemberName("");
      setMemberEmail("");
      setMemberPassword("");
      void queryClient.invalidateQueries({ queryKey: ["agency"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Failed to add team member",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  const changePlanMutation = useMutation({
    mutationFn: () => saasService.changeSubscriptionPlan(selectedTier, selectedCycle),
    onSuccess: (sub) => {
      pushToast({
        variant: "success",
        title: `Switched to ${sub.plan?.name ?? selectedTier}`,
      });
      void queryClient.invalidateQueries({ queryKey: ["agency"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Plan update failed",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  const data = dashboardQuery.data;
  const agency = data?.agency;
  const sub = data?.subscription;

  return (
    <DashboardShell
      portal="agency"
      title={agency ? agency.name : "Agency Workspace"}
      subtitle="Tenant-isolated operations, AI configuration, and subscription usage"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {agency && (
            <Badge variant={agency.status === "ACTIVE" ? "success" : "warning"}>
              {agency.status}
            </Badge>
          )}
          {user && <Badge variant="info">{user.role}</Badge>}
        </div>
        <div className="flex gap-2">
          <Link href="/agency/branding">
            <Button variant="secondary" size="sm">
              Branding &amp; Fees
            </Button>
          </Link>
          <Link href="/workspace/inbox">
            <Button size="sm">Open Agent Inbox</Button>
          </Link>
        </div>
      </div>

      {agency && agency.status !== "ACTIVE" && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
          <div>
            <p className="font-medium">Agency status: {agency.status}</p>
            <p className="text-[var(--muted-foreground)]">
              Operational endpoints remain locked until a Platform Super Admin approves your agency.
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Customers</CardDescription>
            <CardTitle className="text-2xl">{data?.customer_count ?? "—"}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Bookings</CardDescription>
            <CardTitle className="text-2xl">{data?.booking_count ?? "—"}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center justify-between">
              <span>AI Conversations</span>
              <Bot className="h-4 w-4 text-[var(--muted-foreground)]" />
            </CardDescription>
            <CardTitle className="text-2xl">{data?.conversation_count ?? "—"}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center justify-between">
              <span>Team Members</span>
              <Users className="h-4 w-4 text-[var(--muted-foreground)]" />
            </CardDescription>
            <CardTitle className="text-2xl">{data?.team_member_count ?? "—"}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-[var(--accent)]" />
              Subscription &amp; Usage
            </CardTitle>
            <CardDescription>
              Current plan: {sub?.plan?.name ?? "—"} ({sub?.status ?? "—"})
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {sub?.plan && (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-[var(--muted-foreground)]">API Requests</span>
                  <span>
                    {sub.api_requests_used} / {sub.plan.monthly_api_limit.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--muted-foreground)]">AI Conversations</span>
                  <span>
                    {sub.conversations_used} /{" "}
                    {sub.plan.monthly_conversation_limit.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--muted-foreground)]">Bookings</span>
                  <span>
                    {sub.bookings_used} / {sub.plan.monthly_booking_limit.toLocaleString()}
                  </span>
                </div>
              </div>
            )}

            {isOwner && agency?.status === "ACTIVE" && (
              <div className="space-y-3 border-t border-[var(--border)] pt-4">
                <p className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
                  Switch SaaS Plan
                </p>
                <div className="flex flex-wrap gap-2">
                  <select
                    value={selectedTier}
                    onChange={(e) => setSelectedTier(e.target.value as SubscriptionTier)}
                    className="h-9 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 text-sm"
                  >
                    <option value="STARTER">Starter</option>
                    <option value="PROFESSIONAL">Professional</option>
                    <option value="BUSINESS">Business</option>
                    <option value="ENTERPRISE">Enterprise</option>
                  </select>
                  <select
                    value={selectedCycle}
                    onChange={(e) => setSelectedCycle(e.target.value as BillingCycle)}
                    className="h-9 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 text-sm"
                  >
                    <option value="MONTHLY">Monthly</option>
                    <option value="ANNUAL">Annual</option>
                  </select>
                  <Button
                    size="sm"
                    onClick={() => changePlanMutation.mutate()}
                    disabled={changePlanMutation.isPending}
                  >
                    Update Plan
                  </Button>
                </div>
              </div>
            )}

            {isOwner && invoicesQuery.data && invoicesQuery.data.length > 0 && (
              <div className="border-t border-[var(--border)] pt-4">
                <p className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
                  Recent Invoices
                </p>
                <ul className="space-y-1.5 text-xs">
                  {invoicesQuery.data.slice(0, 5).map((inv) => (
                    <li key={inv.id} className="flex justify-between">
                      <span className="font-mono">{inv.invoice_number}</span>
                      <span>
                        ${inv.amount_usd} · {inv.status}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>

        {canViewTeam && (
          <Card>
            <CardHeader>
              <CardTitle>Agency Team</CardTitle>
              <CardDescription>Staff scoped exclusively to this tenant.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <ul className="divide-y divide-[var(--border)] text-sm">
                {teamQuery.data?.map((member) => (
                  <li key={member.id} className="flex items-center justify-between py-2">
                    <div>
                      <p className="font-medium">{member.full_name}</p>
                      <p className="text-xs text-[var(--muted-foreground)]">{member.email}</p>
                    </div>
                    <Badge>{member.role}</Badge>
                  </li>
                ))}
              </ul>

              {isOwner && agency?.status === "ACTIVE" && (
                <form
                  onSubmit={(e: React.FormEvent) => {
                    e.preventDefault();
                    addMemberMutation.mutate();
                  }}
                  className="space-y-3 border-t border-[var(--border)] pt-4"
                >
                  <p className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
                    Add Staff Member
                  </p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <Input
                      placeholder="Full name"
                      value={memberName}
                      onChange={(e) => setMemberName(e.target.value)}
                      required
                    />
                    <Input
                      type="email"
                      placeholder="staff@agency.com"
                      value={memberEmail}
                      onChange={(e) => setMemberEmail(e.target.value)}
                      required
                    />
                    <Input
                      type="password"
                      placeholder="Temporary password (8+ chars)"
                      value={memberPassword}
                      onChange={(e) => setMemberPassword(e.target.value)}
                      required
                    />
                    <select
                      value={memberRole}
                      onChange={(e) =>
                        setMemberRole(e.target.value as "TRAVEL_AGENT" | "AGENCY_MANAGER")
                      }
                      className="h-10 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 text-sm"
                    >
                      <option value="TRAVEL_AGENT">Travel Agent</option>
                      <option value="AGENCY_MANAGER">Agency Manager</option>
                    </select>
                  </div>
                  <Button type="submit" size="sm" disabled={addMemberMutation.isPending}>
                    Add Team Member
                  </Button>
                </form>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardShell>
  );
}

export default function AgencyDashboardPage() {
  return (
    <RoleGuard allowedRoles={["AGENCY_OWNER", "AGENCY_MANAGER", "TRAVEL_AGENT"]}>
      <AgencyDashboardContent />
    </RoleGuard>
  );
}
