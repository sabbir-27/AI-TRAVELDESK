"use client";

import { useQuery } from "@tanstack/react-query";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { saasService } from "@/services/saas-service";

function BillingContent() {
  const dashQuery = useQuery({
    queryKey: ["admin", "dashboard"],
    queryFn: () => saasService.getAdminDashboard(),
  });
  const subsQuery = useQuery({
    queryKey: ["admin", "subscriptions"],
    queryFn: () => saasService.listAdminSubscriptions(),
  });

  return (
    <DashboardShell portal="admin" title="Platform Billing" subtitle="SaaS subscription MRR and tenant billing">
      <Card>
        <CardHeader>
          <CardDescription>Monthly Recurring Revenue</CardDescription>
          <CardTitle className="text-3xl">
            ${dashQuery.data?.monthly_recurring_revenue_usd ?? "0.00"}
          </CardTitle>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Subscribed Tenants</CardTitle>
        </CardHeader>
        <CardContent>
          {!subsQuery.data || subsQuery.data.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)]">No tenant subscriptions yet.</p>
          ) : (
            <ul className="divide-y divide-[var(--border)] text-sm">
              {subsQuery.data.map((row) => (
                <li key={row.subscription.id} className="flex items-center justify-between py-2.5">
                  <div>
                    <p className="font-medium">{row.agency_name}</p>
                    <p className="text-xs text-[var(--muted-foreground)]">
                      {row.subscription.plan?.name} · {row.subscription.billing_cycle}
                    </p>
                  </div>
                  <Badge variant={row.subscription.status === "ACTIVE" ? "success" : "warning"}>
                    {row.subscription.status}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </DashboardShell>
  );
}

export default function AdminBillingPage() {
  return (
    <RoleGuard allowedRoles={["SUPER_ADMIN"]}>
      <BillingContent />
    </RoleGuard>
  );
}
