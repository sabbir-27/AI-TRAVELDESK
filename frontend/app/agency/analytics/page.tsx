"use client";

import { useQuery } from "@tanstack/react-query";

import { SimpleBarChart } from "@/components/charts/simple-bar-chart";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { saasService } from "@/services/saas-service";

function AgencyAnalyticsContent() {
  const dashQuery = useQuery({
    queryKey: ["agency", "dashboard"],
    queryFn: () => saasService.getAgencyDashboard(),
  });

  const data = dashQuery.data;

  return (
    <DashboardShell
      portal="agency"
      title="Agency Analytics"
      subtitle="Live tenant operational and quota metrics"
    >
      {dashQuery.isLoading || !data ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Operational Volume</CardTitle>
              <CardDescription>Customers, bookings, conversations, and staff</CardDescription>
            </CardHeader>
            <CardContent>
              <SimpleBarChart
                data={[
                  { name: "Customers", value: data.customer_count },
                  { name: "Bookings", value: data.booking_count },
                  { name: "Chats", value: data.conversation_count },
                  { name: "Team", value: data.team_member_count },
                ]}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Metered SaaS Quota Usage</CardTitle>
              <CardDescription>Current billing cycle consumption</CardDescription>
            </CardHeader>
            <CardContent>
              <SimpleBarChart
                data={[
                  { name: "API Calls", value: data.subscription?.api_requests_used ?? 0 },
                  { name: "AI Chats", value: data.subscription?.conversations_used ?? 0 },
                  { name: "Bookings", value: data.subscription?.bookings_used ?? 0 },
                ]}
              />
            </CardContent>
          </Card>
        </div>
      )}
    </DashboardShell>
  );
}

export default function AgencyAnalyticsPage() {
  return (
    <RoleGuard allowedRoles={["AGENCY_OWNER", "AGENCY_MANAGER"]}>
      <AgencyAnalyticsContent />
    </RoleGuard>
  );
}
