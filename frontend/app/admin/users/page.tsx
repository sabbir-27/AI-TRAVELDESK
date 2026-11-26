"use client";

import { useQuery } from "@tanstack/react-query";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { saasService } from "@/services/saas-service";

function UsersContent() {
  const usersQuery = useQuery({
    queryKey: ["admin", "users"],
    queryFn: () => saasService.listAdminUsers(),
  });

  return (
    <DashboardShell portal="admin" title="Users" subtitle="Platform-wide user accounts and RBAC roles">
      <Card>
        <CardHeader>
          <CardTitle>Registered Users</CardTitle>
        </CardHeader>
        <CardContent>
          {usersQuery.isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                    <th className="pb-2 font-medium">Name</th>
                    <th className="pb-2 font-medium">Email</th>
                    <th className="pb-2 font-medium">Role</th>
                    <th className="pb-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {usersQuery.data?.map((u) => (
                    <tr key={u.id}>
                      <td className="py-2.5 font-medium">{u.full_name}</td>
                      <td className="py-2.5 text-[var(--muted-foreground)]">{u.email}</td>
                      <td className="py-2.5">
                        <Badge>{u.role}</Badge>
                      </td>
                      <td className="py-2.5">
                        <Badge variant={u.is_active ? "success" : "neutral"}>
                          {u.is_active ? "Active" : "Disabled"}
                        </Badge>
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

export default function AdminUsersPage() {
  return (
    <RoleGuard allowedRoles={["SUPER_ADMIN"]}>
      <UsersContent />
    </RoleGuard>
  );
}
