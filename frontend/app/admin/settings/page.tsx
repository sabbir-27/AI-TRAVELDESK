"use client";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function AdminSettingsPage() {
  return (
    <RoleGuard allowedRoles={["SUPER_ADMIN"]}>
      <DashboardShell
        portal="admin"
        title="Platform Settings"
        subtitle="Security controls, tenant isolation policies, and environment posture"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">PostgreSQL Row-Level Security</CardTitle>
                <Badge variant="success">Enforced</Badge>
              </div>
              <CardDescription>
                FORCE ROW LEVEL SECURITY active on 21 tenant-scoped tables.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-[var(--muted-foreground)]">
              Session context is derived solely from verified JWT claims and agency memberships.
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Refresh Token Rotation</CardTitle>
                <Badge variant="success">Enforced</Badge>
              </div>
              <CardDescription>
                One-time refresh rotation with automatic token-family revocation on replay.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-[var(--muted-foreground)]">
              Access tokens expire in 15 minutes; passwords hashed using Argon2id.
            </CardContent>
          </Card>
        </div>
      </DashboardShell>
    </RoleGuard>
  );
}
