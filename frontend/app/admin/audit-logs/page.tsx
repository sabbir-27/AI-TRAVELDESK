"use client";

import { useQuery } from "@tanstack/react-query";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { saasService } from "@/services/saas-service";

function AuditLogsContent() {
  const logsQuery = useQuery({
    queryKey: ["admin", "audit-logs"],
    queryFn: () => saasService.listAdminAuditLogs(),
  });

  return (
    <DashboardShell portal="admin" title="Audit Logs" subtitle="Immutable security and tenant lifecycle trail">
      <Card>
        <CardHeader>
          <CardTitle>Recent Audit Events</CardTitle>
        </CardHeader>
        <CardContent>
          {logsQuery.isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !logsQuery.data || logsQuery.data.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)]">No audit events recorded yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                    <th className="pb-2 font-medium">Action</th>
                    <th className="pb-2 font-medium">Resource</th>
                    <th className="pb-2 font-medium">IP</th>
                    <th className="pb-2 font-medium">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {logsQuery.data.map((log) => (
                    <tr key={log.id}>
                      <td className="py-2.5 font-mono text-xs">
                        <Badge>{log.action}</Badge>
                      </td>
                      <td className="py-2.5 text-xs text-[var(--muted-foreground)]">
                        {log.resource_type} {log.resource_id ? `(${log.resource_id.slice(0, 8)}...)` : ""}
                      </td>
                      <td className="py-2.5 font-mono text-xs">{log.ip_address ?? "—"}</td>
                      <td className="py-2.5 text-xs text-[var(--muted-foreground)]">
                        {new Date(log.created_at).toLocaleString()}
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

export default function AdminAuditLogsPage() {
  return (
    <RoleGuard allowedRoles={["SUPER_ADMIN"]}>
      <AuditLogsContent />
    </RoleGuard>
  );
}
