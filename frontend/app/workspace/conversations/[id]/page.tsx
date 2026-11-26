"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Send, Sparkles } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import React, { useState } from "react";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api-client";
import { saasService } from "@/services/saas-service";

function ConversationDetailContent() {
  const params = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const { pushToast } = useToast();

  const [replyText, setReplyText] = useState("");
  const [isInternalNote, setIsInternalNote] = useState(false);

  const convQuery = useQuery({
    queryKey: ["workspace", "conversation", params.id],
    queryFn: () => saasService.getWorkspaceConversation(params.id),
    enabled: Boolean(params.id),
    refetchInterval: 5000,
  });

  const suggestionsQuery = useQuery({
    queryKey: ["workspace", "suggestions", params.id],
    queryFn: () => saasService.getWorkspaceSuggestions(params.id),
    enabled: Boolean(params.id),
  });

  const takeoverMutation = useMutation({
    mutationFn: (action: "takeover" | "release" | "resolve") =>
      saasService.takeoverWorkspaceConversation(params.id, action),
    onSuccess: (updated) => {
      pushToast({ variant: "success", title: `Conversation status: ${updated.status}` });
      void queryClient.invalidateQueries({ queryKey: ["workspace"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Action failed",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  const replyMutation = useMutation({
    mutationFn: () =>
      saasService.replyWorkspaceConversation(params.id, replyText, isInternalNote),
    onSuccess: () => {
      setReplyText("");
      void queryClient.invalidateQueries({
        queryKey: ["workspace", "conversation", params.id],
      });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Failed to post message",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  const conv = convQuery.data;

  return (
    <DashboardShell
      portal="workspace"
      title={`Conversation ${params.id.slice(0, 8)}...`}
      subtitle="Human takeover, AI-generated response suggestions, and internal case notes"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link href="/workspace/inbox" className="text-sm text-[var(--accent)] hover:underline">
          ← Back to inbox
        </Link>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="info">{conv?.status ?? "LOADING"}</Badge>
          <Button
            size="sm"
            onClick={() => takeoverMutation.mutate("takeover")}
            disabled={takeoverMutation.isPending}
          >
            Take Over Chat
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => takeoverMutation.mutate("release")}
            disabled={takeoverMutation.isPending}
          >
            Release to AI
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => takeoverMutation.mutate("resolve")}
            disabled={takeoverMutation.isPending}
          >
            Resolve
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        <Card className="lg:col-span-8 flex flex-col">
          <CardHeader>
            <CardTitle>Message Thread</CardTitle>
            <CardDescription>
              Language: {conv?.detected_language ?? "—"} · Channel: {conv?.channel ?? "—"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {convQuery.isLoading ? (
              <Skeleton className="h-44 w-full" />
            ) : !conv || conv.messages.length === 0 ? (
              <p className="text-sm text-[var(--muted-foreground)]">No messages recorded yet.</p>
            ) : (
              <div className="max-h-96 space-y-2.5 overflow-y-auto pr-1">
                {conv.messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`rounded-lg border p-3 text-xs whitespace-pre-line ${
                      msg.is_internal_note
                        ? "border-amber-500/40 bg-amber-500/10"
                        : "border-[var(--border)] bg-[var(--background)]"
                    }`}
                  >
                    <div className="mb-1 flex items-center justify-between text-[10px] text-[var(--muted-foreground)]">
                      <span className="font-semibold">
                        {msg.is_internal_note ? "INTERNAL NOTE" : msg.sender_type}
                      </span>
                      <span>{new Date(msg.created_at).toLocaleString()}</span>
                    </div>
                    {msg.content}
                  </div>
                ))}
              </div>
            )}

            <form
              onSubmit={(e: React.FormEvent) => {
                e.preventDefault();
                if (!replyText.trim()) return;
                replyMutation.mutate();
              }}
              className="space-y-2 border-t border-[var(--border)] pt-4"
            >
              <textarea
                rows={3}
                placeholder={
                  isInternalNote ? "Write an internal shift note..." : "Reply to traveler..."
                }
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-xs"
              />
              <div className="flex flex-wrap items-center justify-between gap-2">
                <label className="flex items-center gap-2 text-xs">
                  <input
                    type="checkbox"
                    checked={isInternalNote}
                    onChange={(e) => setIsInternalNote(e.target.checked)}
                  />
                  <span>Save as internal note (hidden from customer)</span>
                </label>
                <Button type="submit" size="sm" disabled={replyMutation.isPending}>
                  <Send className="h-3.5 w-3.5" />
                  {isInternalNote ? "Add Internal Note" : "Send Reply"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <div className="space-y-6 lg:col-span-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Sparkles className="h-4 w-4 text-[var(--accent)]" />
                AI Reply Suggestions
              </CardTitle>
              <CardDescription>Click a suggestion to load it into the composer.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-xs">
              {suggestionsQuery.data?.suggestions.map((text, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setIsInternalNote(false);
                    setReplyText(text);
                  }}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] p-2.5 text-left hover:border-[var(--accent)]"
                >
                  {text}
                </button>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Customer &amp; Bookings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              {conv?.customer ? (
                <div>
                  <p className="font-medium">{conv.customer.full_name}</p>
                  <p className="text-[var(--muted-foreground)]">{conv.customer.email}</p>
                </div>
              ) : (
                <p className="text-[var(--muted-foreground)]">Anonymous / widget visitor</p>
              )}

              {conv?.bookings && conv.bookings.length > 0 && (
                <div className="border-t border-[var(--border)] pt-2 space-y-1">
                  <p className="font-medium">Linked Bookings</p>
                  {conv.bookings.map((b) => (
                    <p key={b.id} className="font-mono">
                      {b.booking_reference} · {b.status}
                    </p>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardShell>
  );
}

export default function WorkspaceConversationDetailPage() {
  return (
    <RoleGuard allowedRoles={["AGENCY_OWNER", "AGENCY_MANAGER", "TRAVEL_AGENT"]}>
      <ConversationDetailContent />
    </RoleGuard>
  );
}
