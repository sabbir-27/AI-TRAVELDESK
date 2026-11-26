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

function BrandingContent() {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const dashQuery = useQuery({
    queryKey: ["agency", "dashboard"],
    queryFn: () => saasService.getAgencyDashboard(),
  });

  const [name, setName] = useState("");
  const [primaryColor, setPrimaryColor] = useState("#0F172A");
  const [secondaryColor, setSecondaryColor] = useState("#2563EB");
  const [feeFlat, setFeeFlat] = useState("0");
  const [feePercent, setFeePercent] = useState("0");

  useEffect(() => {
    if (dashQuery.data?.agency) {
      const a = dashQuery.data.agency;
      setName(a.name);
      setPrimaryColor(a.primary_color);
      setSecondaryColor(a.secondary_color);
      setFeeFlat(String(a.service_fee_flat));
      setFeePercent(String(a.service_fee_percent));
    }
  }, [dashQuery.data]);

  const updateMutation = useMutation({
    mutationFn: () =>
      saasService.updateAgencyProfile({
        name,
        primary_color: primaryColor,
        secondary_color: secondaryColor,
        service_fee_flat: Number(feeFlat),
        service_fee_percent: Number(feePercent),
      }),
    onSuccess: () => {
      pushToast({ variant: "success", title: "White-label branding & fees saved" });
      void queryClient.invalidateQueries({ queryKey: ["agency"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Save failed",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  return (
    <DashboardShell
      portal="agency"
      title="White-Label Branding & Service Fees"
      subtitle="Customize customer-facing identity and agency markup rules"
    >
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Brand Identity &amp; Pricing Markup</CardTitle>
          <CardDescription>Changes persist directly to your agency profile.</CardDescription>
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
              <label className="text-sm font-medium">Brand Display Name</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} required />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Primary Color (Hex)</label>
                <Input
                  value={primaryColor}
                  onChange={(e) => setPrimaryColor(e.target.value)}
                  pattern="^#[0-9A-Fa-f]{6}$"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Secondary Color (Hex)</label>
                <Input
                  value={secondaryColor}
                  onChange={(e) => setSecondaryColor(e.target.value)}
                  pattern="^#[0-9A-Fa-f]{6}$"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Flat Service Fee</label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={feeFlat}
                  onChange={(e) => setFeeFlat(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Percentage Markup (%)</label>
                <Input
                  type="number"
                  step="0.1"
                  min="0"
                  max="50"
                  value={feePercent}
                  onChange={(e) => setFeePercent(e.target.value)}
                />
              </div>
            </div>

            <Button type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending ? "Saving..." : "Save Branding & Fees"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </DashboardShell>
  );
}

export default function AgencyBrandingPage() {
  return (
    <RoleGuard allowedRoles={["AGENCY_OWNER"]}>
      <BrandingContent />
    </RoleGuard>
  );
}
