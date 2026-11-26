"use client";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const INTEGRATIONS = [
  { name: "SSLCommerz", category: "Payment (Bangladesh)", phase: "Phase 7" },
  { name: "bKash & Nagad", category: "Mobile Wallet (Bangladesh)", phase: "Phase 7" },
  { name: "Stripe", category: "International Cards", phase: "Phase 7" },
  { name: "SMTP / SendGrid / FCM", category: "Notifications", phase: "Phase 7" },
];

export default function AdminIntegrationsPage() {
  return (
    <RoleGuard allowedRoles={["SUPER_ADMIN"]}>
      <DashboardShell
        portal="admin"
        title="Platform Integrations"
        subtitle="Global payment gateways and notification channels"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          {INTEGRATIONS.map((item) => (
            <Card key={item.name}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{item.name}</CardTitle>
                  <Badge>{item.phase}</Badge>
                </div>
                <CardDescription>{item.category}</CardDescription>
              </CardHeader>
              <CardContent className="text-xs text-[var(--muted-foreground)]">
                Configured with signed webhook verification and idempotent transaction keys.
              </CardContent>
            </Card>
          ))}
        </div>
      </DashboardShell>
    </RoleGuard>
  );
}
