"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import React, { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api-client";
import { saasService } from "@/services/saas-service";

function AgencySettingsContent() {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();

  const dashQuery = useQuery({
    queryKey: ["agency", "dashboard"],
    queryFn: () => saasService.getAgencyDashboard(),
  });

  const [contactEmail, setContactEmail] = useState("");
  const [name, setName] = useState("");

  useEffect(() => {
    if (dashQuery.data?.agency) {
      setName(dashQuery.data.agency.name);
      setContactEmail(dashQuery.data.agency.contact_email);
    }
  }, [dashQuery.data]);

  const updateMutation = useMutation({
    mutationFn: () => saasService.updateAgencyProfile({ name, contact_email: contactEmail }),
    onSuccess: () => {
      pushToast({ variant: "success", title: "Agency settings updated" });
      void queryClient.invalidateQueries({ queryKey: ["agency"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Update failed",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  return (
    <DashboardShell
      portal="agency"
      title="Agency Settings"
      subtitle="Core tenant contact and profile settings"
    >
      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle>General Settings</CardTitle>
          <CardDescription>
            Tenant Slug: <span className="font-mono">{dashQuery.data?.agency.slug ?? "—"}</span>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={(e: React.FormEvent) => {
              e.preventDefault();
              updateMutation.mutate();
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Agency Name</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Contact Email</label>
              <Input
                type="email"
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
                required
              />
            </div>
            <Button type="submit" disabled={updateMutation.isPending}>
              Save Settings
            </Button>
          </form>
        </CardContent>
      </Card>
    </DashboardShell>
  );
}

export default function AgencySettingsPage() {
  return (
    <RoleGuard allowedRoles={["AGENCY_OWNER"]}>
      <AgencySettingsContent />
    </RoleGuard>
  );
}
