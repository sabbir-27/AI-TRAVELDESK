"use client";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const SUPPLIERS = [
  { name: "Amadeus GDS / NDC", mode: "Adapter Interface Ready", phase: "Phase 5" },
  { name: "Duffel Flights API", mode: "Adapter Interface Ready", phase: "Phase 5" },
  { name: "Sabre GDS", mode: "Adapter Interface Ready", phase: "Phase 5" },
  { name: "Travelport", mode: "Adapter Interface Ready", phase: "Phase 5" },
];

export default function AdminFlightSuppliersPage() {
  return (
    <RoleGuard allowedRoles={["SUPER_ADMIN"]}>
      <DashboardShell
        portal="admin"
        title="Flight Suppliers"
        subtitle="Authorized GDS & NDC flight provider adapters"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          {SUPPLIERS.map((s) => (
            <Card key={s.name}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{s.name}</CardTitle>
                  <Badge variant="info">{s.phase}</Badge>
                </div>
                <CardDescription>{s.mode}</CardDescription>
              </CardHeader>
              <CardContent className="text-xs text-[var(--muted-foreground)]">
                Decoupled supplier adapters enforce offer revalidation and transaction logging
                before reservation creation.
              </CardContent>
            </Card>
          ))}
        </div>
      </DashboardShell>
    </RoleGuard>
  );
}
