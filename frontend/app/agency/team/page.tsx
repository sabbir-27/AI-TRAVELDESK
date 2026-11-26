"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import React, { useState } from "react";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api-client";
import { saasService } from "@/services/saas-service";

function AgencyTeamContent() {
  const { user } = useAuth();
  const isOwner = user?.role === "AGENCY_OWNER";
  const queryClient = useQueryClient();
  const { pushToast } = useToast();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"TRAVEL_AGENT" | "AGENCY_MANAGER">("TRAVEL_AGENT");

  const teamQuery = useQuery({
    queryKey: ["agency", "team"],
    queryFn: () => saasService.listTeamMembers(),
  });

  const addMutation = useMutation({
    mutationFn: () =>
      saasService.addTeamMember({ full_name: fullName, email, password, role }),
    onSuccess: (member) => {
      pushToast({ variant: "success", title: `Added ${member.full_name}` });
      setFullName("");
      setEmail("");
      setPassword("");
      void queryClient.invalidateQueries({ queryKey: ["agency", "team"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Failed to add member",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  return (
    <DashboardShell
      portal="agency"
      title="Team & RBAC"
      subtitle="Manage agency managers and human travel agents"
    >
      <div className="grid gap-6 lg:grid-cols-12">
        <Card className="lg:col-span-7">
          <CardHeader>
            <CardTitle>Active Staff</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y divide-[var(--border)] text-sm">
              {teamQuery.data?.map((m) => (
                <li key={m.id} className="flex items-center justify-between py-2.5">
                  <div>
                    <p className="font-medium">{m.full_name}</p>
                    <p className="text-xs text-[var(--muted-foreground)]">{m.email}</p>
                  </div>
                  <Badge>{m.role}</Badge>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        {isOwner && (
          <Card className="lg:col-span-5">
            <CardHeader>
              <CardTitle>Invite Staff Member</CardTitle>
              <CardDescription>Assign AGENCY_MANAGER or TRAVEL_AGENT access.</CardDescription>
            </CardHeader>
            <CardContent>
              <form
                onSubmit={(e: React.FormEvent) => {
                  e.preventDefault();
                  addMutation.mutate();
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
                  placeholder="agent@agency.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                <Input
                  type="password"
                  placeholder="Temporary password (8+ chars)"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <select
                  value={role}
                  onChange={(e) =>
                    setRole(e.target.value as "TRAVEL_AGENT" | "AGENCY_MANAGER")
                  }
                  className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 text-sm"
                >
                  <option value="TRAVEL_AGENT">Travel Agent</option>
                  <option value="AGENCY_MANAGER">Agency Manager</option>
                </select>
                <Button type="submit" className="w-full" disabled={addMutation.isPending}>
                  Add Staff Member
                </Button>
              </form>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardShell>
  );
}

export default function AgencyTeamPage() {
  return (
    <RoleGuard allowedRoles={["AGENCY_OWNER", "AGENCY_MANAGER"]}>
      <AgencyTeamContent />
    </RoleGuard>
  );
}
