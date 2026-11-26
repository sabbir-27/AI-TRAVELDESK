"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { saasService } from "@/services/saas-service";

export default function AgencyConversationsPage() {
  const convQuery = useQuery({
    queryKey: ["agency", "conversations"],
    queryFn: () => saasService.listAgencyConversations(),
  });

  return (
    <RoleGuard allowedRoles={["AGENCY_OWNER", "AGENCY_MANAGER", "TRAVEL_AGENT"]}>
      <DashboardShell
        portal="agency"
        title="Conversations"
        subtitle="Customer AI and human-handoff threads"
      >
        <Card>
          <CardHeader>
            <CardTitle>Conversation History</CardTitle>
          </CardHeader>
          <CardContent>
            {convQuery.isLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : !convQuery.data || convQuery.data.length === 0 ? (
              <p className="text-sm text-[var(--muted-foreground)]">
                No conversations recorded yet. AI chat threads activate in Phases 4 and 6.
              </p>
            ) : (
              <ul className="divide-y divide-[var(--border)] text-sm">
                {convQuery.data.map((c) => (
                  <li key={c.id} className="flex items-center justify-between py-2.5">
                    <div>
                      <Link
                        href={`/workspace/conversations/${c.id}`}
                        className="font-mono text-xs hover:underline"
                      >
                        {c.id}
                      </Link>
                      <p className="text-xs text-[var(--muted-foreground)]">
                        Channel: {c.channel} · Language: {c.detected_language}
                      </p>
                    </div>
                    <Badge>{c.status}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </DashboardShell>
    </RoleGuard>
  );
}
