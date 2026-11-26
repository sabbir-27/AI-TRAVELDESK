"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api-client";
import { saasService } from "@/services/saas-service";

function AgencyBookingsContent() {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();

  const bookingsQuery = useQuery({
    queryKey: ["agency", "bookings"],
    queryFn: () => saasService.listAgencyBookings(),
  });

  const issueMutation = useMutation({
    mutationFn: (bookingId: string) => saasService.issueBookingTickets(bookingId),
    onSuccess: (res) => {
      pushToast({ variant: "success", title: res.message });
      void queryClient.invalidateQueries({ queryKey: ["agency", "bookings"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Ticketing failed",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (bookingId: string) =>
      saasService.cancelBooking(bookingId, "Cancelled by agency operations"),
    onSuccess: (res) => {
      pushToast({ variant: "info", title: `Booking updated (${res.booking_status})` });
      void queryClient.invalidateQueries({ queryKey: ["agency", "bookings"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Cancellation failed",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  const refundMutation = useMutation({
    mutationFn: (bookingId: string) =>
      saasService.refundBooking(bookingId, "Agency refund processed"),
    onSuccess: (res) => {
      pushToast({ variant: "success", title: `Refunded $${res.amount}` });
      void queryClient.invalidateQueries({ queryKey: ["agency", "bookings"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Refund failed",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  return (
    <RoleGuard allowedRoles={["AGENCY_OWNER", "AGENCY_MANAGER", "TRAVEL_AGENT"]}>
      <DashboardShell
        portal="agency"
        title="Agency Bookings"
        subtitle="Reservations, ticketing recovery, cancellations, and refunds"
      >
        <Card>
          <CardHeader>
            <CardTitle>Reservations &amp; Lifecycle Actions</CardTitle>
          </CardHeader>
          <CardContent>
            {bookingsQuery.isLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : !bookingsQuery.data || bookingsQuery.data.length === 0 ? (
              <p className="text-sm text-[var(--muted-foreground)]">
                No bookings recorded for this agency yet.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                      <th className="pb-2 font-medium">Reference</th>
                      <th className="pb-2 font-medium">PNR</th>
                      <th className="pb-2 font-medium">Status</th>
                      <th className="pb-2 font-medium">Total</th>
                      <th className="pb-2 text-right font-medium">Actions</th>
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
                        <td className="py-2.5 text-right space-x-2">
                          {(b.status === "PAYMENT_CONFIRMED" ||
                            b.status === "TICKETING_FAILED") && (
                            <Button
                              size="sm"
                              onClick={() => issueMutation.mutate(b.id)}
                              disabled={issueMutation.isPending}
                            >
                              {b.status === "TICKETING_FAILED"
                                ? "Retry Ticketing"
                                : "Issue Ticket"}
                            </Button>
                          )}
                          {b.status !== "CANCELLED" && b.status !== "REFUND_PENDING" && (
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => cancelMutation.mutate(b.id)}
                              disabled={cancelMutation.isPending}
                            >
                              Cancel
                            </Button>
                          )}
                          {b.status === "REFUND_PENDING" && (
                            <Button
                              size="sm"
                              variant="danger"
                              onClick={() => refundMutation.mutate(b.id)}
                              disabled={refundMutation.isPending}
                            >
                              Process Refund
                            </Button>
                          )}
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
    </RoleGuard>
  );
}

export default function AgencyBookingsPage() {
  return <AgencyBookingsContent />;
}
