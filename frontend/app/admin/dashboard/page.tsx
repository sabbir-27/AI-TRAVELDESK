"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, CheckCircle2, DollarSign, Users } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { SimpleBarChart } from "@/components/charts/simple-bar-chart";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api-client";
import { saasService } from "@/services/saas-service";
import type { AgencyStatus } from "@/types/saas";

function statusVariant(status: AgencyStatus) {
  if (status === "ACTIVE") return "success";
  if (status === "PENDING") return "warning";
  return "neutral";
}

function AdminDashboardContent() {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [statusFilter, setStatusFilter] = useState<string>("");

  const dashboardQuery = useQuery({
    queryKey: ["admin", "dashboard"],
    queryFn: () => saasService.getAdminDashboard(),
  });

  const agenciesQuery = useQuery({
    queryKey: ["admin", "agencies", statusFilter],
    queryFn: () => saasService.listAdminAgencies(statusFilter || undefined),
  });

  const approveMutation = useMutation({
    mutationFn: (agencyId: string) => saasService.approveAgency(agencyId, "Approved by Super Admin"),
    onSuccess: (agency) => {
      pushToast({ variant: "success", title: `Approved ${agency.name}` });
      void queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Approval failed",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  const suspendMutation = useMutation({
    mutationFn: (agencyId: string) =>
      saasService.suspendAgency(agencyId, "Suspended by Super Admin"),
    onSuccess: (agency) => {
      pushToast({ variant: "info", title: `Suspended ${agency.name}` });
      void queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Suspension failed",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  const stats = dashboardQuery.data;

  return (
    <DashboardShell
      portal="admin"
      title="Super Admin Dashboard"
      subtitle="Global multi-tenant governance, approvals, and revenue telemetry"
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center justify-between">
              <span>Total Agencies</span>
              <Building2 className="h-4 w-4 text-[var(--muted-foreground)]" />
            </CardDescription>
            <CardTitle className="text-2xl">{stats?.total_agencies ?? "—"}</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-[var(--muted-foreground)]">
            {stats?.active_agencies ?? 0} active · {stats?.pending_agencies ?? 0} pending
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center justify-between">
              <span>Active Subscriptions</span>
              <CheckCircle2 className="h-4 w-4 text-[var(--muted-foreground)]" />
            </CardDescription>
            <CardTitle className="text-2xl">{stats?.active_subscriptions ?? "—"}</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-[var(--muted-foreground)]">
            {stats?.suspended_agencies ?? 0} suspended agencies
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center justify-between">
              <span>Monthly Recurring Revenue</span>
              <DollarSign className="h-4 w-4 text-[var(--muted-foreground)]" />
            </CardDescription>
            <CardTitle className="text-2xl">
              ${stats?.monthly_recurring_revenue_usd ?? "0.00"}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-[var(--muted-foreground)]">
            Live active subscription MRR
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center justify-between">
              <span>Platform Users</span>
              <Users className="h-4 w-4 text-[var(--muted-foreground)]" />
            </CardDescription>
            <CardTitle className="text-2xl">{stats?.total_users ?? "—"}</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-[var(--muted-foreground)]">
            {stats?.total_bookings ?? 0} bookings recorded
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        <Card className="lg:col-span-7">
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 space-y-0">
            <div>
              <CardTitle>Travel Agency Tenants</CardTitle>
              <CardDescription>Approve pending agencies or suspend tenants.</CardDescription>
            </div>
            <select
              aria-label="Filter agencies by status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-9 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 text-sm"
            >
              <option value="">All statuses</option>
              <option value="PENDING">Pending</option>
              <option value="ACTIVE">Active</option>
              <option value="SUSPENDED">Suspended</option>
            </select>
          </CardHeader>
          <CardContent>
            {agenciesQuery.isLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : !agenciesQuery.data || agenciesQuery.data.length === 0 ? (
              <p className="text-sm text-[var(--muted-foreground)]">No agencies registered yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                      <th className="pb-2 font-medium">Agency</th>
                      <th className="pb-2 font-medium">Status</th>
                      <th className="pb-2 text-right font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border)]">
                    {agenciesQuery.data.map((agency) => (
                      <tr key={agency.id}>
                        <td className="py-3">
                          <Link
                            href={`/admin/agencies/${agency.id}`}
                            className="font-medium hover:underline"
                          >
                            {agency.name}
                          </Link>
                          <p className="font-mono text-xs text-[var(--muted-foreground)]">
                            {agency.slug}
                          </p>
                        </td>
                        <td className="py-3">
                          <Badge variant={statusVariant(agency.status)}>{agency.status}</Badge>
                        </td>
                        <td className="py-3 text-right space-x-2">
                          {agency.status !== "ACTIVE" && (
                            <Button
                              size="sm"
                              onClick={() => approveMutation.mutate(agency.id)}
                              disabled={approveMutation.isPending}
                            >
                              Approve
                            </Button>
                          )}
                          {agency.status !== "SUSPENDED" && (
                            <Button
                              size="sm"
                              variant="danger"
                              onClick={() => suspendMutation.mutate(agency.id)}
                              disabled={suspendMutation.isPending}
                            >
                              Suspend
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-5">
          <CardHeader>
            <CardTitle>Tenant Status Distribution</CardTitle>
            <CardDescription>Real-time count by lifecycle status.</CardDescription>
          </CardHeader>
          <CardContent>
            {stats ? (
              <SimpleBarChart
                data={[
                  { name: "Active", value: stats.active_agencies },
                  { name: "Pending", value: stats.pending_agencies },
                  { name: "Suspended", value: stats.suspended_agencies },
                ]}
              />
            ) : (
              <Skeleton className="h-60 w-full" />
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardShell>
  );
}

export default function AdminDashboardPage() {
  return (
    <RoleGuard allowedRoles={["SUPER_ADMIN"]}>
      <AdminDashboardContent />
    </RoleGuard>
  );
}
