"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { saasService } from "@/services/saas-service";

function AdminAgenciesContent() {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const agenciesQuery = useQuery({
    queryKey: ["admin", "agencies", statusFilter],
    queryFn: () => saasService.listAdminAgencies(statusFilter || undefined),
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => saasService.approveAgency(id, "Approved via directory"),
    onSuccess: (a) => {
      pushToast({ variant: "success", title: `Approved ${a.name}` });
      void queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
  });

  const suspendMutation = useMutation({
    mutationFn: (id: string) => saasService.suspendAgency(id, "Suspended via directory"),
    onSuccess: (a) => {
      pushToast({ variant: "info", title: `Suspended ${a.name}` });
      void queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
  });

  const filtered = (agenciesQuery.data ?? []).filter(
    (a) =>
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.slug.toLowerCase().includes(search.toLowerCase()) ||
      a.contact_email.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <DashboardShell portal="admin" title="Agencies" subtitle="Manage onboarded travel agency tenants">
      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 space-y-0">
          <div>
            <CardTitle>All Registered Agencies</CardTitle>
            <CardDescription>Click an agency to inspect tenant metrics.</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Input
              placeholder="Search name, slug, email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-56"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-10 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 text-sm"
            >
              <option value="">All statuses</option>
              <option value="PENDING">Pending</option>
              <option value="ACTIVE">Active</option>
              <option value="SUSPENDED">Suspended</option>
            </select>
          </div>
        </CardHeader>
        <CardContent>
          {agenciesQuery.isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : filtered.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)]">No matching agencies.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                    <th className="pb-2 font-medium">Name</th>
                    <th className="pb-2 font-medium">Slug</th>
                    <th className="pb-2 font-medium">Contact</th>
                    <th className="pb-2 font-medium">Currency</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 text-right font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {filtered.map((agency) => (
                    <tr key={agency.id}>
                      <td className="py-3 font-medium">
                        <Link href={`/admin/agencies/${agency.id}`} className="hover:underline">
                          {agency.name}
                        </Link>
                      </td>
                      <td className="py-3 font-mono text-xs">{agency.slug}</td>
                      <td className="py-3 text-[var(--muted-foreground)]">{agency.contact_email}</td>
                      <td className="py-3">{agency.default_currency}</td>
                      <td className="py-3">
                        <Badge variant={agency.status === "ACTIVE" ? "success" : "warning"}>
                          {agency.status}
                        </Badge>
                      </td>
                      <td className="py-3 text-right space-x-2">
                        {agency.status !== "ACTIVE" && (
                          <Button size="sm" onClick={() => approveMutation.mutate(agency.id)}>
                            Approve
                          </Button>
                        )}
                        {agency.status !== "SUSPENDED" && (
                          <Button
                            size="sm"
                            variant="danger"
                            onClick={() => suspendMutation.mutate(agency.id)}
                          >
                            Suspend
                          </Button>
                        )}
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

export default function AdminAgenciesPage() {
  return (
    <RoleGuard allowedRoles={["SUPER_ADMIN"]}>
      <AdminAgenciesContent />
    </RoleGuard>
  );
}
