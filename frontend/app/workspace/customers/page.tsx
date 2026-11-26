"use client";

import { useQuery } from "@tanstack/react-query";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { saasService } from "@/services/saas-service";

export default function WorkspaceCustomersPage() {
  const customersQuery = useQuery({
    queryKey: ["agency", "customers"],
    queryFn: () => saasService.listAgencyCustomers(),
  });

  return (
    <RoleGuard allowedRoles={["AGENCY_OWNER", "AGENCY_MANAGER", "TRAVEL_AGENT"]}>
      <DashboardShell
        portal="workspace"
        title="Traveler Profiles"
        subtitle="Customer records visible to assigned travel agents"
      >
        <Card>
          <CardHeader>
            <CardTitle>Customers</CardTitle>
          </CardHeader>
          <CardContent>
            {customersQuery.isLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : !customersQuery.data || customersQuery.data.length === 0 ? (
              <p className="text-sm text-[var(--muted-foreground)]">No customers found.</p>
            ) : (
              <ul className="divide-y divide-[var(--border)] text-sm">
                {customersQuery.data.map((c) => (
                  <li key={c.id} className="flex items-center justify-between py-2.5">
                    <div>
                      <p className="font-medium">{c.full_name}</p>
                      <p className="text-xs text-[var(--muted-foreground)]">{c.email}</p>
                    </div>
                    <span className="text-xs uppercase text-[var(--muted-foreground)]">
                      {c.preferred_language}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </DashboardShell>
    </RoleGuard>
  );
}
