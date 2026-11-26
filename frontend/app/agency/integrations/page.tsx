"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Code2, Copy, Globe, KeyRound, Trash2 } from "lucide-react";
import React, { useEffect, useState } from "react";

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
import type { ApiKeyIssuedDto, WidgetTokenIssuedDto } from "@/types/saas";

function AgencyIntegrationsContent() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const isOwner = user?.role === "AGENCY_OWNER";

  const [originsText, setOriginsText] = useState("http://localhost:3000");
  const [issuedWidget, setIssuedWidget] = useState<WidgetTokenIssuedDto | null>(null);
  const [keyLabel, setKeyLabel] = useState("Production Website Key");
  const [issuedApiKey, setIssuedApiKey] = useState<ApiKeyIssuedDto | null>(null);

  const integrationsQuery = useQuery({
    queryKey: ["agency", "integrations"],
    queryFn: () => saasService.listAgencyIntegrations(),
  });

  const widgetIntegration = integrationsQuery.data?.find(
    (i) => i.integration_type === "WIDGET"
  );
  const apiIntegration = integrationsQuery.data?.find(
    (i) => i.integration_type === "REST_API"
  );

  useEffect(() => {
    if (widgetIntegration && widgetIntegration.allowed_origins.length > 0) {
      setOriginsText(widgetIntegration.allowed_origins.join("\n"));
    }
  }, [widgetIntegration]);

  const parsedOrigins = () =>
    originsText
      .split(/\r?\n|,/)
      .map((s) => s.trim())
      .filter(Boolean);

  const rotateWidgetMutation = useMutation({
    mutationFn: () => saasService.issueWidgetToken(parsedOrigins()),
    onSuccess: (res) => {
      setIssuedWidget(res);
      pushToast({ variant: "success", title: "Scoped public widget token issued" });
      void queryClient.invalidateQueries({ queryKey: ["agency", "integrations"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Failed to issue widget token",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  const saveOriginsMutation = useMutation({
    mutationFn: () => saasService.updateWidgetOrigins(parsedOrigins()),
    onSuccess: () => {
      pushToast({ variant: "success", title: "Allowed widget origins updated" });
      void queryClient.invalidateQueries({ queryKey: ["agency", "integrations"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Failed to update origins",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  const createKeyMutation = useMutation({
    mutationFn: () => saasService.createApiKey(keyLabel),
    onSuccess: (res) => {
      setIssuedApiKey(res);
      pushToast({ variant: "success", title: "Server REST API key created" });
      void queryClient.invalidateQueries({ queryKey: ["agency", "integrations"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Failed to create API key",
        description: err instanceof ApiError ? err.detail : "Agency must be ACTIVE",
      });
    },
  });

  const revokeKeyMutation = useMutation({
    mutationFn: (credentialId: string) => saasService.revokeApiKey(credentialId),
    onSuccess: () => {
      pushToast({ variant: "info", title: "API key revoked" });
      void queryClient.invalidateQueries({ queryKey: ["agency", "integrations"] });
    },
  });

  const copyText = (value: string, label: string) => {
    void navigator.clipboard?.writeText(value);
    pushToast({ variant: "info", title: `${label} copied` });
  };

  return (
    <DashboardShell
      portal="agency"
      title="Website & API Integrations"
      subtitle="Manage embeddable widget tokens, origin allowlists, and server-to-server REST API keys"
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <Globe className="h-4 w-4 text-[var(--accent)]" />
                JavaScript Chatbot Widget
              </CardTitle>
              <Badge variant="info">Origin-Scoped Public Token</Badge>
            </div>
            <CardDescription>
              Embed on any agency webpage without exposing private REST API keys.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium">Allowed Origins (one per line)</label>
              <textarea
                rows={3}
                value={originsText}
                onChange={(e) => setOriginsText(e.target.value)}
                className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 font-mono text-xs"
              />
            </div>

            {isOwner && (
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  onClick={() => rotateWidgetMutation.mutate()}
                  disabled={rotateWidgetMutation.isPending}
                >
                  Generate / Rotate Widget Token
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => saveOriginsMutation.mutate()}
                  disabled={saveOriginsMutation.isPending}
                >
                  Save Allowed Origins
                </Button>
              </div>
            )}

            {issuedWidget && (
              <div className="space-y-2 rounded-lg border border-[var(--border)] bg-[var(--muted)] p-3">
                <div className="flex items-center justify-between text-xs font-medium">
                  <span>Embed Snippet</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => copyText(issuedWidget.embed_snippet, "Embed snippet")}
                  >
                    <Copy className="h-3.5 w-3.5" />
                    Copy
                  </Button>
                </div>
                <pre className="overflow-x-auto text-xs">{issuedWidget.embed_snippet}</pre>
              </div>
            )}

            {widgetIntegration && widgetIntegration.credentials.length > 0 && (
              <div className="space-y-1 text-xs text-[var(--muted-foreground)]">
                <p className="font-medium text-[var(--foreground)]">Issued Widget Tokens</p>
                {widgetIntegration.credentials.map((c) => (
                  <div key={c.id} className="flex justify-between">
                    <span className="font-mono">{c.key_prefix}...</span>
                    <Badge variant={c.is_active ? "success" : "neutral"}>
                      {c.is_active ? "Active" : "Rotated"}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <Code2 className="h-4 w-4 text-[var(--accent)]" />
                Server-to-Server REST API Keys
              </CardTitle>
              <Badge>X-API-Key</Badge>
            </div>
            <CardDescription>
              Hashed with SHA-256 at rest; plaintext secrets are displayed once on creation.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {isOwner && (
              <form
                onSubmit={(e: React.FormEvent) => {
                  e.preventDefault();
                  createKeyMutation.mutate();
                }}
                className="flex gap-2"
              >
                <Input
                  placeholder="API key label"
                  value={keyLabel}
                  onChange={(e) => setKeyLabel(e.target.value)}
                  required
                />
                <Button type="submit" size="sm" disabled={createKeyMutation.isPending}>
                  <KeyRound className="h-3.5 w-3.5" />
                  Create Key
                </Button>
              </form>
            )}

            {issuedApiKey && (
              <div className="space-y-1.5 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs">
                <div className="flex items-center justify-between font-medium">
                  <span>Save this API key now (shown once)</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => copyText(issuedApiKey.api_key, "API key")}
                  >
                    <Copy className="h-3.5 w-3.5" />
                    Copy
                  </Button>
                </div>
                <p className="break-all font-mono">{issuedApiKey.api_key}</p>
              </div>
            )}

            <div className="space-y-2 text-xs">
              {!apiIntegration || apiIntegration.credentials.length === 0 ? (
                <p className="text-[var(--muted-foreground)]">No REST API keys issued yet.</p>
              ) : (
                apiIntegration.credentials.map((cred) => (
                  <div
                    key={cred.id}
                    className="flex items-center justify-between rounded-lg border border-[var(--border)] px-3 py-2"
                  >
                    <div>
                      <p className="font-mono">{cred.key_prefix}...</p>
                      <p className="text-[10px] text-[var(--muted-foreground)]">
                        Created {new Date(cred.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={cred.is_active ? "success" : "neutral"}>
                        {cred.is_active ? "Active" : "Revoked"}
                      </Badge>
                      {isOwner && cred.is_active && (
                        <Button
                          size="sm"
                          variant="ghost"
                          aria-label="Revoke API key"
                          onClick={() => revokeKeyMutation.mutate(cred.id)}
                        >
                          <Trash2 className="h-3.5 w-3.5 text-red-500" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardShell>
  );
}

export default function AgencyIntegrationsPage() {
  return (
    <RoleGuard allowedRoles={["AGENCY_OWNER", "AGENCY_MANAGER"]}>
      <AgencyIntegrationsContent />
    </RoleGuard>
  );
}
