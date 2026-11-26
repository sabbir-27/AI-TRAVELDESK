"use client";

import { useQuery } from "@tanstack/react-query";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { saasService } from "@/services/saas-service";

function BookingsContent() {
  const bookingsQuery = useQuery({
    queryKey: ["admin", "bookings"],
    queryFn: () => saasService.listAdminBookings(),
  });

  return (
    <DashboardShell portal="admin" title="Global Bookings" subtitle="Cross-tenant booking monitoring">
      <Card>
        <CardHeader>
          <CardTitle>Booking Ledger</CardTitle>
        </CardHeader>
        <CardContent>
          {bookingsQuery.isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !bookingsQuery.data || bookingsQuery.data.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)]">
              No bookings recorded yet. Live reservations are wired in Phases 5 and 7.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                    <th className="pb-2 font-medium">Reference</th>
                    <th className="pb-2 font-medium">PNR</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {bookingsQuery.data.map((b) => (
                    <tr key={b.id}>
                      <td className="py-2.5 font-mono text-xs">{b.booking_reference}</td>
                      <td className="py-2.5 font-mono text-xs">{b.pnr ?? "—"}</td>
                      <td className="py-2.5">
                        <Badge>{b.status}</Badge>
                      </td>
                      <td className="py-2.5">
                        {b.currency} {b.total_amount}
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

export default function AdminBookingsPage() {
  return (
    <RoleGuard allowedRoles={["SUPER_ADMIN"]}>
      <BookingsContent />
    </RoleGuard>
  );
}
