"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";

export default function DashboardPage() {
  const router = useRouter();
  const { user, isLoading, isAuthenticated } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || !user) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <Skeleton className="h-36 w-full" />
      </div>
    );
  }

  return (
    <DashboardShell
      portal="customer"
      title="Account Workspace"
      subtitle="Authenticated session verified against FastAPI /api/v1/auth/me"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Badge variant="success">{user.role}</Badge>
        <Link href="/book">
          <Button size="sm">Search &amp; Book Flights</Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Authenticated Profile</CardTitle>
          <CardDescription>Identity and tenant context derived from JWT claims.</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-[var(--muted-foreground)]">Full Name</dt>
              <dd className="font-medium">{user.full_name}</dd>
            </div>
            <div>
              <dt className="text-[var(--muted-foreground)]">Email</dt>
              <dd className="font-medium">{user.email}</dd>
            </div>
            <div>
              <dt className="text-[var(--muted-foreground)]">User ID</dt>
              <dd className="font-mono text-xs">{user.id}</dd>
            </div>
            <div>
              <dt className="text-[var(--muted-foreground)]">Assigned Agency Tenant</dt>
              <dd className="font-mono text-xs">
                {user.default_agency_id ?? "None (customer account)"}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </DashboardShell>
  );
}
