"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import React, { useState } from "react";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api-client";
import { saasService } from "@/services/saas-service";

function AgencyCustomersContent() {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");

  const customersQuery = useQuery({
    queryKey: ["agency", "customers"],
    queryFn: () => saasService.listAgencyCustomers(),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      saasService.createAgencyCustomer({
        full_name: fullName,
        email,
        phone: phone || undefined,
      }),
    onSuccess: (cust) => {
      pushToast({ variant: "success", title: `Added customer ${cust.full_name}` });
      setFullName("");
      setEmail("");
      setPhone("");
      void queryClient.invalidateQueries({ queryKey: ["agency", "customers"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Failed to add customer",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  return (
    <RoleGuard allowedRoles={["AGENCY_OWNER", "AGENCY_MANAGER", "TRAVEL_AGENT"]}>
      <DashboardShell
        portal="agency"
        title="Customers"
        subtitle="Traveler records scoped exclusively to your agency"
      >
        <div className="grid gap-6 lg:grid-cols-12">
          <Card className="lg:col-span-7">
            <CardHeader>
              <CardTitle>Customer Directory</CardTitle>
            </CardHeader>
            <CardContent>
              {customersQuery.isLoading ? (
                <Skeleton className="h-32 w-full" />
              ) : !customersQuery.data || customersQuery.data.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No customers added yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                        <th className="pb-2 font-medium">Name</th>
                        <th className="pb-2 font-medium">Email</th>
                        <th className="pb-2 font-medium">Language</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border)]">
                      {customersQuery.data.map((c) => (
                        <tr key={c.id}>
                          <td className="py-2.5 font-medium">{c.full_name}</td>
                          <td className="py-2.5 text-[var(--muted-foreground)]">{c.email}</td>
                          <td className="py-2.5 uppercase text-xs">{c.preferred_language}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="lg:col-span-5">
            <CardHeader>
              <CardTitle>Add Customer</CardTitle>
              <CardDescription>Create a traveler record in your tenant.</CardDescription>
            </CardHeader>
            <CardContent>
              <form
                onSubmit={(e: React.FormEvent) => {
                  e.preventDefault();
                  createMutation.mutate();
                }}
                className="space-y-3"
              >
                <Input
                  placeholder="Full name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                />
                <Input
                  type="email"
                  placeholder="traveler@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                <Input
                  placeholder="Phone (optional)"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
                <Button type="submit" className="w-full" disabled={createMutation.isPending}>
                  Create Customer
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </DashboardShell>
    </RoleGuard>
  );
}

export default function AgencyCustomersPage() {
  return <AgencyCustomersContent />;
}
