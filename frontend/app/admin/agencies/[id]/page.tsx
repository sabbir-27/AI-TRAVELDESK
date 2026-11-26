"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { saasService } from "@/services/saas-service";

function AgencyDetailContent() {
  const params = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const { pushToast } = useToast();

  const detailQuery = useQuery({
    queryKey: ["admin", "agency", params.id],
    queryFn: () => saasService.getAdminAgencyDetail(params.id),
    enabled: Boolean(params.id),
  });

  const approveMutation = useMutation({
    mutationFn: () => saasService.approveAgency(params.id, "Approved from detail view"),
    onSuccess: (a) => {
      pushToast({ variant: "success", title: `Approved ${a.name}` });
      void queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
  });

  const suspendMutation = useMutation({
    mutationFn: () => saasService.suspendAgency(params.id, "Suspended from detail view"),
    onSuccess: (a) => {
      pushToast({ variant: "info", title: `Suspended ${a.name}` });
      void queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
  });

  const detail = detailQuery.data;

  return (
    <DashboardShell
      portal="admin"
      title={detail ? detail.agency.name : "Agency Detail"}
      subtitle="Tenant inspection and subscription status"
    >
      <div className="flex items-center justify-between">
        <Link href="/admin/agencies" className="text-sm text-[var(--accent)] hover:underline">
          ← Back to agencies
        </Link>
        {detail && (
          <div className="space-x-2">
            {detail.agency.status !== "ACTIVE" && (
              <Button size="sm" onClick={() => approveMutation.mutate()}>
                Approve Agency
              </Button>
            )}
            {detail.agency.status !== "SUSPENDED" && (
              <Button size="sm" variant="danger" onClick={() => suspendMutation.mutate()}>
                Suspend Agency
              </Button>
            )}
          </div>
        )}
      </div>

      {detailQuery.isLoading || !detail ? (
        <Skeleton className="h-48 w-full" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Status</CardDescription>
              <CardTitle>
                <Badge variant={detail.agency.status === "ACTIVE" ? "success" : "warning"}>
                  {detail.agency.status}
                </Badge>
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Staff Members</CardDescription>
              <CardTitle className="text-2xl">{detail.member_count}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Customers</CardDescription>
              <CardTitle className="text-2xl">{detail.customer_count}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Bookings</CardDescription>
              <CardTitle className="text-2xl">{detail.booking_count}</CardTitle>
            </CardHeader>
          </Card>
        </div>
      )}

      {detail && (
        <Card>
          <CardHeader>
            <CardTitle>Tenant Configuration</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <p className="text-[var(--muted-foreground)]">Slug</p>
              <p className="font-mono">{detail.agency.slug}</p>
            </div>
            <div>
              <p className="text-[var(--muted-foreground)]">Contact Email</p>
              <p>{detail.agency.contact_email}</p>
            </div>
            <div>
              <p className="text-[var(--muted-foreground)]">Plan</p>
              <p>{detail.subscription?.plan?.name ?? "None"}</p>
            </div>
            <div>
              <p className="text-[var(--muted-foreground)]">Subscription Status</p>
              <p>{detail.subscription?.status ?? "—"}</p>
            </div>
          </CardContent>
        </Card>
      )}
    </DashboardShell>
  );
}

export default function AdminAgencyDetailPage() {
  return (
    <RoleGuard allowedRoles={["SUPER_ADMIN"]}>
      <AgencyDetailContent />
    </RoleGuard>
  );
}
