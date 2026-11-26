"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api-client";
import { saasService } from "@/services/saas-service";
import type { BillingCycle, SubscriptionTier } from "@/types/saas";

function AgencyBillingContent() {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [tier, setTier] = useState<SubscriptionTier>("PROFESSIONAL");
  const [cycle, setCycle] = useState<BillingCycle>("MONTHLY");

  const dashQuery = useQuery({
    queryKey: ["agency", "dashboard"],
    queryFn: () => saasService.getAgencyDashboard(),
  });
  const invoicesQuery = useQuery({
    queryKey: ["agency", "invoices"],
    queryFn: () => saasService.listInvoices(),
  });

  const changeMutation = useMutation({
    mutationFn: () => saasService.changeSubscriptionPlan(tier, cycle),
    onSuccess: (sub) => {
      pushToast({ variant: "success", title: `Updated plan to ${sub.plan?.name ?? tier}` });
      void queryClient.invalidateQueries({ queryKey: ["agency"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Plan update failed",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  const sub = dashQuery.data?.subscription;

  return (
    <DashboardShell
      portal="agency"
      title="Billing & Subscription"
      subtitle="Manage SaaS plan tier, billing cycle, and generated invoices"
    >
      <Card>
        <CardHeader>
          <CardTitle>Active Subscription</CardTitle>
          <CardDescription>
            Plan: {sub?.plan?.name ?? "—"} · Status: {sub?.status ?? "—"} · Cycle:{" "}
            {sub?.billing_cycle ?? "—"}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3">
          <select
            value={tier}
            onChange={(e) => setTier(e.target.value as SubscriptionTier)}
            className="h-10 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 text-sm"
          >
            <option value="STARTER">Starter ($49/mo)</option>
            <option value="PROFESSIONAL">Professional ($149/mo)</option>
            <option value="BUSINESS">Business ($399/mo)</option>
            <option value="ENTERPRISE">Enterprise ($999/mo)</option>
          </select>
          <select
            value={cycle}
            onChange={(e) => setCycle(e.target.value as BillingCycle)}
            className="h-10 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 text-sm"
          >
            <option value="MONTHLY">Monthly</option>
            <option value="ANNUAL">Annual</option>
          </select>
          <Button onClick={() => changeMutation.mutate()} disabled={changeMutation.isPending}>
            Switch Plan
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Invoices</CardTitle>
        </CardHeader>
        <CardContent>
          {!invoicesQuery.data || invoicesQuery.data.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)]">No invoices generated yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                    <th className="pb-2 font-medium">Invoice #</th>
                    <th className="pb-2 font-medium">Amount</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Due Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {invoicesQuery.data.map((inv) => (
                    <tr key={inv.id}>
                      <td className="py-2.5 font-mono text-xs">{inv.invoice_number}</td>
                      <td className="py-2.5">${inv.amount_usd}</td>
                      <td className="py-2.5">
                        <Badge>{inv.status}</Badge>
                      </td>
                      <td className="py-2.5 text-xs text-[var(--muted-foreground)]">
                        {new Date(inv.due_at).toLocaleDateString()}
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

export default function AgencyBillingPage() {
  return (
    <RoleGuard allowedRoles={["AGENCY_OWNER"]}>
      <AgencyBillingContent />
    </RoleGuard>
  );
}
