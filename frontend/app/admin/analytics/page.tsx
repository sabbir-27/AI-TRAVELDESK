"use client";

import { useQuery } from "@tanstack/react-query";

import { SimpleBarChart } from "@/components/charts/simple-bar-chart";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { saasService } from "@/services/saas-service";

function AnalyticsContent() {
  const dashQuery = useQuery({
    queryKey: ["admin", "dashboard"],
    queryFn: () => saasService.getAdminDashboard(),
  });

  const stats = dashQuery.data;

  return (
    <DashboardShell
      portal="admin"
      title="Platform Analytics"
      subtitle="Live SaaS tenant, user, and booking volume metrics"
    >
      {dashQuery.isLoading || !stats ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Agency Lifecycle Breakdown</CardTitle>
              <CardDescription>Active vs Pending vs Suspended agencies</CardDescription>
            </CardHeader>
            <CardContent>
              <SimpleBarChart
                data={[
                  { name: "Active", value: stats.active_agencies },
                  { name: "Pending", value: stats.pending_agencies },
                  { name: "Suspended", value: stats.suspended_agencies },
                ]}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Platform Scale Summary</CardTitle>
              <CardDescription>Users, active subscriptions, and bookings</CardDescription>
            </CardHeader>
            <CardContent>
              <SimpleBarChart
                data={[
                  { name: "Agencies", value: stats.total_agencies },
                  { name: "Users", value: stats.total_users },
                  { name: "Subscriptions", value: stats.active_subscriptions },
                  { name: "Bookings", value: stats.total_bookings },
                ]}
              />
            </CardContent>
          </Card>
        </div>
      )}
    </DashboardShell>
  );
}

export default function AdminAnalyticsPage() {
  return (
    <RoleGuard allowedRoles={["SUPER_ADMIN"]}>
      <AnalyticsContent />
    </RoleGuard>
  );
}
