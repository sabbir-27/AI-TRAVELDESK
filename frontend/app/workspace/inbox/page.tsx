"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LifeBuoy, MessageSquare, UserCheck } from "lucide-react";
import Link from "next/link";
import React, { useState } from "react";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api-client";
import { saasService } from "@/services/saas-service";

function WorkspaceInboxContent() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const canAssign = user?.role === "AGENCY_OWNER" || user?.role === "AGENCY_MANAGER";

  const [statusFilter, setStatusFilter] = useState("");
  const [ticketSubject, setTicketSubject] = useState("");
  const [ticketPriority, setTicketPriority] = useState<"LOW" | "MEDIUM" | "HIGH" | "URGENT">(
    "MEDIUM"
  );

  const inboxQuery = useQuery({
    queryKey: ["workspace", "inbox", statusFilter],
    queryFn: () => saasService.getWorkspaceInbox(statusFilter || undefined),
    refetchInterval: 5000,
  });

  const teamQuery = useQuery({
    queryKey: ["agency", "team"],
    queryFn: () => saasService.listTeamMembers(),
    enabled: canAssign,
  });

  const ticketsQuery = useQuery({
    queryKey: ["workspace", "tickets"],
    queryFn: () => saasService.listSupportTickets(),
  });

  const assignMutation = useMutation({
    mutationFn: ({ convId, userId }: { convId: string; userId: string }) =>
      saasService.assignWorkspaceConversation(convId, userId, "Assigned from workspace inbox"),
    onSuccess: () => {
      pushToast({ variant: "success", title: "Conversation assigned" });
      void queryClient.invalidateQueries({ queryKey: ["workspace", "inbox"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Assignment failed",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  const createTicketMutation = useMutation({
    mutationFn: () =>
      saasService.createSupportTicket({ subject: ticketSubject, priority: ticketPriority }),
    onSuccess: () => {
      pushToast({ variant: "success", title: "Support ticket created" });
      setTicketSubject("");
      void queryClient.invalidateQueries({ queryKey: ["workspace", "tickets"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Ticket creation failed",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  const updateTicketMutation = useMutation({
    mutationFn: ({
      id,
      status,
    }: {
      id: string;
      status: "OPEN" | "IN_PROGRESS" | "WAITING_CUSTOMER" | "RESOLVED" | "CLOSED";
    }) => saasService.updateSupportTicket(id, { status }),
    onSuccess: () => {
      pushToast({ variant: "info", title: "Ticket status updated" });
      void queryClient.invalidateQueries({ queryKey: ["workspace", "tickets"] });
    },
  });

  return (
    <DashboardShell
      portal="workspace"
      title="Human Agent Inbox"
      subtitle="Live conversation queue, agent assignment, and support ticket management"
    >
      <div className="grid gap-6 lg:grid-cols-12">
        <Card className="lg:col-span-7">
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 space-y-0">
            <div>
              <CardTitle className="flex items-center gap-2 text-base">
                <MessageSquare className="h-4 w-4 text-[var(--accent)]" />
                Conversation Queue
              </CardTitle>
              <CardDescription>Auto-refreshes every 5 seconds.</CardDescription>
            </div>
            <select
              aria-label="Filter conversations"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-9 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 text-sm"
            >
              <option value="">All conversations</option>
              <option value="HUMAN_HANDOFF">Needs Human Handoff</option>
              <option value="HUMAN_ACTIVE">Human Active</option>
              <option value="AI_ACTIVE">AI Active</option>
              <option value="RESOLVED">Resolved</option>
            </select>
          </CardHeader>
          <CardContent>
            {inboxQuery.isLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : !inboxQuery.data || inboxQuery.data.length === 0 ? (
              <p className="text-sm text-[var(--muted-foreground)]">
                No conversations in queue yet.
              </p>
            ) : (
              <ul className="divide-y divide-[var(--border)] text-sm">
                {inboxQuery.data.map((c) => (
                  <li key={c.id} className="space-y-2 py-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="font-medium">
                          {c.customer_name ?? `Visitor (${c.id.slice(0, 8)})`}
                        </p>
                        <p className="text-xs text-[var(--muted-foreground)]">
                          {c.channel} · {c.detected_language}
                          {c.assigned_to_name ? ` · Assigned: ${c.assigned_to_name}` : ""}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={c.status === "HUMAN_HANDOFF" ? "warning" : "info"}>
                          {c.status}
                        </Badge>
                        <Link href={`/workspace/conversations/${c.id}`}>
                          <Button size="sm" variant="secondary">
                            <UserCheck className="h-3.5 w-3.5" />
                            Open
                          </Button>
                        </Link>
                      </div>
                    </div>
                    {c.last_message_preview && (
                      <p className="truncate text-xs text-[var(--muted-foreground)]">
                        {c.last_message_preview}
                      </p>
                    )}
                    {canAssign && teamQuery.data && teamQuery.data.length > 0 && (
                      <div className="flex items-center gap-2 pt-1">
                        <select
                          aria-label={`Assign conversation ${c.id}`}
                          defaultValue={c.assigned_to_user_id ?? ""}
                          onChange={(e) => {
                            if (e.target.value) {
                              assignMutation.mutate({ convId: c.id, userId: e.target.value });
                            }
                          }}
                          className="h-8 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-2 text-xs"
                        >
                          <option value="">Assign to staff...</option>
                          {teamQuery.data.map((m) => (
                            <option key={m.user_id} value={m.user_id}>
                              {m.full_name} ({m.role})
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <LifeBuoy className="h-4 w-4 text-[var(--accent)]" />
              Support Tickets
            </CardTitle>
            <CardDescription>Escalated cases and ticketing-failure recovery items.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <form
              onSubmit={(e: React.FormEvent) => {
                e.preventDefault();
                if (!ticketSubject.trim()) return;
                createTicketMutation.mutate();
              }}
              className="space-y-2"
            >
              <Input
                placeholder="Ticket subject..."
                value={ticketSubject}
                onChange={(e) => setTicketSubject(e.target.value)}
                required
              />
              <div className="flex gap-2">
                <select
                  value={ticketPriority}
                  onChange={(e) =>
                    setTicketPriority(e.target.value as "LOW" | "MEDIUM" | "HIGH" | "URGENT")
                  }
                  className="h-9 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-2 text-xs"
                >
                  <option value="LOW">Low</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HIGH">High</option>
                  <option value="URGENT">Urgent</option>
                </select>
                <Button type="submit" size="sm" disabled={createTicketMutation.isPending}>
                  Create Ticket
                </Button>
              </div>
            </form>

            <ul className="divide-y divide-[var(--border)] text-xs">
              {ticketsQuery.data?.map((t) => (
                <li key={t.id} className="space-y-1.5 py-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{t.subject}</span>
                    <Badge variant={t.priority === "URGENT" ? "warning" : "neutral"}>
                      {t.priority}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[var(--muted-foreground)]">{t.status}</span>
                    <select
                      value={t.status}
                      onChange={(e) =>
                        updateTicketMutation.mutate({
                          id: t.id,
                          status: e.target.value as
                            | "OPEN"
                            | "IN_PROGRESS"
                            | "WAITING_CUSTOMER"
                            | "RESOLVED"
                            | "CLOSED",
                        })
                      }
                      className="h-7 rounded border border-[var(--border)] bg-[var(--surface)] px-1.5 text-[11px]"
                    >
                      <option value="OPEN">OPEN</option>
                      <option value="IN_PROGRESS">IN_PROGRESS</option>
                      <option value="WAITING_CUSTOMER">WAITING_CUSTOMER</option>
                      <option value="RESOLVED">RESOLVED</option>
                      <option value="CLOSED">CLOSED</option>
                    </select>
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </DashboardShell>
  );
}

export default function WorkspaceInboxPage() {
  return (
    <RoleGuard allowedRoles={["AGENCY_OWNER", "AGENCY_MANAGER", "TRAVEL_AGENT"]}>
      <WorkspaceInboxContent />
    </RoleGuard>
  );
}
