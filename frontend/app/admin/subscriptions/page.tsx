"use client";

import { useQuery } from "@tanstack/react-query";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { saasService } from "@/services/saas-service";

function SubscriptionsContent() {
  const subsQuery = useQuery({
    queryKey: ["admin", "subscriptions"],
    queryFn: () => saasService.listAdminSubscriptions(),
  });

  return (
    <DashboardShell portal="admin" title="Subscriptions" subtitle="Active and trialing agency SaaS plans">
      <Card>
        <CardHeader>
          <CardTitle>Agency Subscriptions</CardTitle>
        </CardHeader>
        <CardContent>
          {subsQuery.isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !subsQuery.data || subsQuery.data.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)]">No subscriptions recorded yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                    <th className="pb-2 font-medium">Agency</th>
                    <th className="pb-2 font-medium">Plan</th>
                    <th className="pb-2 font-medium">Cycle</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Usage (API / Chats / Bookings)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {subsQuery.data.map((row) => (
                    <tr key={row.subscription.id}>
                      <td className="py-2.5 font-medium">{row.agency_name}</td>
                      <td className="py-2.5">{row.subscription.plan?.name ?? "—"}</td>
                      <td className="py-2.5">{row.subscription.billing_cycle}</td>
                      <td className="py-2.5">
                        <Badge variant={row.subscription.status === "ACTIVE" ? "success" : "warning"}>
                          {row.subscription.status}
                        </Badge>
                      </td>
                      <td className="py-2.5 text-xs text-[var(--muted-foreground)]">
                        {row.subscription.api_requests_used} / {row.subscription.conversations_used} /{" "}
                        {row.subscription.bookings_used}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </DashboardShell>
  );
}

export default function AdminSubscriptionsPage() {
  return (
    <RoleGuard allowedRoles={["SUPER_ADMIN"]}>
      <SubscriptionsContent />
    </RoleGuard>
  );
}
