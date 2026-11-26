"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, CheckCircle2, Info, Plane, Scale, ShieldAlert } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { PublicShell } from "@/components/layout/public-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api-client";
import { saasService } from "@/services/saas-service";
import type { BookingCreatedDto, PaymentDto, TicketDto } from "@/types/saas";

interface OfferView {
  id: string;
  isApiBacked: boolean;
  airline: string;
  code: string;
  origin: string;
  destination: string;
  departureTime: string;
  departureHour: number;
  arrivalTime: string;
  duration: string;
  stops: number;
  cabin: string;
  baggage: string;
  refundable: boolean;
  changeFeeUsd: number;
  priceUsd: number;
  isSandbox: boolean;
}

const SANDBOX_SAMPLE_OFFERS: OfferView[] = [
  {
    id: "sandbox-1",
    isApiBacked: false,
    airline: "Emirates",
    code: "EK-583",
    origin: "DAC",
    destination: "DXB",
    departureTime: "10:15",
    departureHour: 10,
    arrivalTime: "13:50",
    duration: "5h 35m",
    stops: 0,
    cabin: "Economy",
    baggage: "30 kg checked + 7 kg cabin",
    refundable: true,
    changeFeeUsd: 75,
    priceUsd: 485,
    isSandbox: true,
  },
  {
    id: "sandbox-2",
    isApiBacked: false,
    airline: "Qatar Airways",
    code: "QR-639",
    origin: "DAC",
    destination: "DXB",
    departureTime: "19:30",
    departureHour: 19,
    arrivalTime: "01:15+1",
    duration: "7h 45m",
    stops: 1,
    cabin: "Economy",
    baggage: "25 kg checked + 7 kg cabin",
    refundable: false,
    changeFeeUsd: 110,
    priceUsd: 420,
    isSandbox: true,
  },
  {
    id: "sandbox-3",
    isApiBacked: false,
    airline: "Biman Bangladesh",
    code: "BG-347",
    origin: "DAC",
    destination: "DXB",
    departureTime: "07:45",
    departureHour: 7,
    arrivalTime: "11:25",
    duration: "5h 40m",
    stops: 0,
    cabin: "Economy",
    baggage: "30 kg checked + 7 kg cabin",
    refundable: true,
    changeFeeUsd: 50,
    priceUsd: 445,
    isSandbox: true,
  },
];

const passengerSchema = z.object({
  first_name: z.string().min(2, "First name is required"),
  last_name: z.string().min(2, "Last name is required"),
  date_of_birth: z.string().min(1, "Date of birth is required"),
  nationality: z.string().length(2, "Use 2-letter ISO nationality code (e.g. BD)"),
  passport_number: z.string().min(6, "Passport number must be at least 6 characters"),
  email: z.string().email("Enter a valid email"),
  phone: z.string().min(6, "Phone number is required"),
});

type PassengerValues = z.infer<typeof passengerSchema>;

export default function BookFlightsPage() {
  const { pushToast } = useToast();
  const { isAuthenticated, user } = useAuth();
  const canCallAgencyFlights =
    isAuthenticated &&
    user !== null &&
    ["AGENCY_OWNER", "AGENCY_MANAGER", "TRAVEL_AGENT"].includes(user.role);

  const [tripType, setTripType] = useState<"one-way" | "round-trip" | "multi-city">("one-way");
  const [origin, setOrigin] = useState("DAC");
  const [destination, setDestination] = useState("DXB");
  const [departureDate, setDepartureDate] = useState("2026-12-15");
  const [returnDate, setReturnDate] = useState("2026-12-22");
  const [cabinClass, setCabinClass] = useState("Economy");
  const [searching, setSearching] = useState(false);
  const [apiOffers, setApiOffers] = useState<OfferView[] | null>(null);

  const [selectedAirlines, setSelectedAirlines] = useState<string[]>([]);
  const [maxPrice, setMaxPrice] = useState<number>(2000);
  const [timeWindow, setTimeWindow] = useState<"all" | "morning" | "afternoon" | "evening">("all");
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [selectedOffer, setSelectedOffer] = useState<OfferView | null>(null);
  const [validatedPassenger, setValidatedPassenger] = useState<PassengerValues | null>(null);
  const [createdBooking, setCreatedBooking] = useState<BookingCreatedDto | null>(null);
  const [submittingBooking, setSubmittingBooking] = useState(false);
  const [gateway, setGateway] = useState<"sslcommerz" | "bkash" | "nagad" | "stripe" | "sandbox">(
    "sslcommerz"
  );
  const [paymentSession, setPaymentSession] = useState<PaymentDto | null>(null);
  const [issuedTickets, setIssuedTickets] = useState<TicketDto[]>([]);
  const [txBusy, setTxBusy] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<PassengerValues>({
    resolver: zodResolver(passengerSchema),
    defaultValues: { nationality: "BD" },
  });

  const baseOffers = useMemo(() => {
    if (apiOffers) return apiOffers;
    return SANDBOX_SAMPLE_OFFERS.map((o) => ({
      ...o,
      origin: origin.toUpperCase() || "DAC",
      destination: destination.toUpperCase() || "DXB",
      cabin: cabinClass,
    }));
  }, [apiOffers, origin, destination, cabinClass]);

  const airlines = useMemo(
    () => Array.from(new Set(baseOffers.map((o) => o.airline))),
    [baseOffers]
  );

  const filteredOffers = useMemo(() => {
    return baseOffers.filter((offer) => {
      if (selectedAirlines.length > 0 && !selectedAirlines.includes(offer.airline)) {
        return false;
      }
      if (offer.priceUsd > maxPrice) return false;
      if (timeWindow === "morning" && offer.departureHour >= 12) return false;
      if (timeWindow === "afternoon" && (offer.departureHour < 12 || offer.departureHour >= 18)) {
        return false;
      }
      if (timeWindow === "evening" && offer.departureHour < 18) return false;
      return true;
    });
  }, [baseOffers, selectedAirlines, maxPrice, timeWindow]);

  const comparedOffers = filteredOffers.filter((o) => compareIds.includes(o.id));

  const runSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatedBooking(null);
    if (!canCallAgencyFlights) {
      setApiOffers(null);
      return;
    }
    setSearching(true);
    try {
      const results = await saasService.searchFlights({
        origin: origin.toUpperCase(),
        destination: destination.toUpperCase(),
        departure_date: departureDate,
        return_date: tripType === "round-trip" ? returnDate : undefined,
        trip_type: tripType,
        adults: 1,
        cabin_class: cabinClass,
      });
      setApiOffers(
        results.map((r) => {
          const dt = new Date(r.departure_at);
          const mins = r.duration_minutes ?? 0;
          return {
            id: r.id,
            isApiBacked: true,
            airline: r.airline ?? r.supplier,
            code: r.flight_number ?? r.supplier_offer_id.slice(0, 8),
            origin: r.origin,
            destination: r.destination,
            departureTime: dt.toISOString().slice(11, 16),
            departureHour: dt.getUTCHours(),
            arrivalTime: "See details",
            duration: mins ? `${Math.floor(mins / 60)}h ${mins % 60}m` : "—",
            stops: r.stops ?? 0,
            cabin: cabinClass,
            baggage: r.baggage ?? "Standard",
            refundable: Boolean(r.refundable),
            changeFeeUsd: 0,
            priceUsd: Number(r.total_fare),
            isSandbox: r.is_sandbox,
          };
        })
      );
      pushToast({ variant: "success", title: `Loaded ${results.length} supplier offers` });
    } catch (err) {
      pushToast({
        variant: "error",
        title: "Supplier search failed",
        description: err instanceof ApiError ? err.detail : "Falling back to preview offers",
      });
    } finally {
      setSearching(false);
    }
  };

  const selectOffer = async (offer: OfferView) => {
    setCreatedBooking(null);
    if (offer.isApiBacked) {
      try {
        const priced = await saasService.priceFlightOffer(offer.id);
        setSelectedOffer({
          ...offer,
          priceUsd: Number(priced.offer.total_fare),
        });
        pushToast({
          variant: "info",
          title: priced.price_changed ? "Fare updated during revalidation" : "Offer price revalidated",
        });
        return;
      } catch (err) {
        pushToast({
          variant: "error",
          title: "Offer pricing failed",
          description: err instanceof ApiError ? err.detail : "Unexpected error",
        });
      }
    }
    setSelectedOffer(offer);
  };

  const toggleAirline = (airline: string) => {
    setSelectedAirlines((prev) =>
      prev.includes(airline) ? prev.filter((a) => a !== airline) : [...prev, airline]
    );
  };

  const toggleCompare = (id: string) => {
    setCompareIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev.slice(-2), id]
    );
  };

  const onPassengerSubmit = async (values: PassengerValues) => {
    setValidatedPassenger(values);
    if (!selectedOffer?.isApiBacked) {
      pushToast({
        variant: "info",
        title: "Passenger details validated",
        description:
          "Sign in with an active agency staff account to create a supplier sandbox reservation via /api/v1/bookings.",
      });
      return;
    }

    setSubmittingBooking(true);
    try {
      const booking = await saasService.createReservation({
        offer_id: selectedOffer.id,
        customer_email: values.email,
        customer_name: `${values.first_name} ${values.last_name}`,
        customer_phone: values.phone,
        passengers: [values],
        idempotency_key: `web-${selectedOffer.id}-${Date.now()}`,
        approved: true,
      });
      setCreatedBooking(booking);
      setPaymentSession(null);
      setIssuedTickets([]);
      pushToast({
        variant: "success",
        title: `Reservation created (${booking.pnr ?? booking.booking_reference})`,
      });
    } catch (err) {
      pushToast({
        variant: "error",
        title: "Reservation failed",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    } finally {
      setSubmittingBooking(false);
    }
  };

  const handlePayAndTicket = async () => {
    if (!createdBooking) return;
    setTxBusy(true);
    try {
      let payment = paymentSession;
      if (!payment) {
        payment = await saasService.initiatePayment({
          booking_id: createdBooking.id,
          gateway,
          idempotency_key: `pay-${createdBooking.id}-${gateway}`,
        });
      }
      const verified = await saasService.verifyPayment(payment.id);
      setPaymentSession(verified);
      const outcome = await saasService.issueBookingTickets(createdBooking.id);
      setIssuedTickets(outcome.tickets);
      setCreatedBooking({ ...createdBooking, status: outcome.booking_status });
      pushToast({ variant: "success", title: outcome.message });
    } catch (err) {
      pushToast({
        variant: "error",
        title: "Transaction step failed",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    } finally {
      setTxBusy(false);
    }
  };

  return (
    <PublicShell>
      <section className="mx-auto max-w-6xl space-y-6 px-4 py-10 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Flight Search &amp; Booking Experience
            </h1>
            <p className="text-sm text-[var(--muted-foreground)]">
              Search flights, revalidate supplier fares, compare rules, and create reservations.
            </p>
          </div>
          <Badge variant={apiOffers ? "info" : "warning"}>
            {apiOffers ? "Connected to /api/v1/flights" : "Public Preview · Sandbox Offers"}
          </Badge>
        </div>

        <div className="flex items-start gap-2.5 rounded-xl border border-blue-500/30 bg-blue-500/10 px-4 py-3 text-xs">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-[var(--accent)]" />
          <span>
            {canCallAgencyFlights
              ? "Authenticated agency mode active: searches invoke /api/v1/flights/search, price revalidates via /api/v1/flights/price, and reservations persist via /api/v1/bookings (marked sandbox when using SandboxFlightAdapter)."
              : "Displayed itineraries are Sandbox Sample Offers. Sign in as an active agency staff user to persist supplier searches and reservations."}
          </span>
        </div>

        <Card>
          <CardContent className="space-y-4 pt-6">
            <div className="flex flex-wrap gap-2 text-xs">
              {(["one-way", "round-trip", "multi-city"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTripType(t)}
                  className={`rounded-lg border px-3 py-1.5 font-medium capitalize ${
                    tripType === t
                      ? "border-[var(--accent)] bg-[var(--accent)] text-[var(--accent-foreground)]"
                      : "border-[var(--border)] bg-[var(--surface)]"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>

            <form onSubmit={runSearch} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              <div className="space-y-1">
                <label htmlFor="flight-origin" className="text-xs font-medium">
                  Origin (IATA)
                </label>
                <Input
                  id="flight-origin"
                  value={origin}
                  maxLength={3}
                  onChange={(e) => setOrigin(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="flight-destination" className="text-xs font-medium">
                  Destination (IATA)
                </label>
                <Input
                  id="flight-destination"
                  value={destination}
                  maxLength={3}
                  onChange={(e) => setDestination(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="flight-depart" className="text-xs font-medium">
                  Departure
                </label>
                <Input
                  id="flight-depart"
                  type="date"
                  value={departureDate}
                  onChange={(e) => setDepartureDate(e.target.value)}
                />
              </div>
              {tripType === "round-trip" && (
                <div className="space-y-1">
                  <label htmlFor="flight-return" className="text-xs font-medium">
                    Return
                  </label>
                  <Input
                    id="flight-return"
                    type="date"
                    value={returnDate}
                    onChange={(e) => setReturnDate(e.target.value)}
                  />
                </div>
              )}
              <div className="space-y-1">
                <label htmlFor="flight-cabin" className="text-xs font-medium">
                  Cabin Class
                </label>
                <select
                  id="flight-cabin"
                  value={cabinClass}
                  onChange={(e) => setCabinClass(e.target.value)}
                  className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 text-sm"
                >
                  <option value="Economy">Economy</option>
                  <option value="Premium Economy">Premium Economy</option>
                  <option value="Business">Business</option>
                </select>
              </div>
              <div className="flex items-end">
                <Button type="submit" className="w-full" disabled={searching}>
                  {searching ? "Searching..." : "Search Flights"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <div className="grid gap-6 lg:grid-cols-12">
          <Card className="h-fit lg:col-span-3">
            <CardHeader>
              <CardTitle className="text-base">Filters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5 text-sm">
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  Airlines
                </p>
                {airlines.map((airline) => (
                  <label key={airline} className="flex items-center gap-2 text-xs">
                    <input
                      type="checkbox"
                      checked={selectedAirlines.includes(airline)}
                      onChange={() => toggleAirline(airline)}
                    />
                    <span>{airline}</span>
                  </label>
                ))}
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                    Max Price
                  </span>
                  <span>${maxPrice}</span>
                </div>
                <input
                  aria-label="Maximum flight price"
                  type="range"
                  min={350}
                  max={2500}
                  step={10}
                  value={maxPrice}
                  onChange={(e) => setMaxPrice(Number(e.target.value))}
                  className="w-full"
                />
              </div>

              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  Departure Window
                </p>
                <select
                  aria-label="Departure time filter"
                  value={timeWindow}
                  onChange={(e) =>
                    setTimeWindow(e.target.value as "all" | "morning" | "afternoon" | "evening")
                  }
                  className="h-9 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-2.5 text-xs"
                >
                  <option value="all">Any time</option>
                  <option value="morning">Morning (Before 12:00)</option>
                  <option value="afternoon">Afternoon (12:00 - 17:59)</option>
                  <option value="evening">Evening (18:00+)</option>
                </select>
              </div>
            </CardContent>
          </Card>

          <div className="space-y-4 lg:col-span-9">
            {filteredOffers.length === 0 ? (
              <Card>
                <CardContent className="p-8 text-center text-sm text-[var(--muted-foreground)]">
                  No offers match the current filters.
                </CardContent>
              </Card>
            ) : (
              filteredOffers.map((offer) => (
                <Card key={offer.id}>
                  <CardContent className="flex flex-wrap items-center justify-between gap-4 p-5">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Plane className="h-4 w-4 text-[var(--accent)]" />
                        <span className="font-semibold">{offer.airline}</span>
                        <span className="font-mono text-xs text-[var(--muted-foreground)]">
                          {offer.code}
                        </span>
                        <Badge variant={offer.refundable ? "success" : "neutral"}>
                          {offer.refundable ? "Refundable" : "Non-refundable"}
                        </Badge>
                        {offer.isSandbox && <Badge variant="warning">Sandbox</Badge>}
                      </div>
                      <p className="text-sm">
                        {offer.origin} {offer.departureTime}{" "}
                        <ArrowRight className="inline h-3.5 w-3.5" /> {offer.destination}{" "}
                        {offer.arrivalTime} · {offer.duration} ·{" "}
                        {offer.stops === 0 ? "Direct" : `${offer.stops} stop`}
                      </p>
                      <p className="text-xs text-[var(--muted-foreground)]">
                        {offer.cabin} · Baggage: {offer.baggage}
                      </p>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <p className="text-xl font-semibold">${offer.priceUsd}</p>
                        <p className="text-[10px] text-[var(--muted-foreground)]">
                          {offer.isSandbox ? "Sandbox fare" : "Live supplier fare"}
                        </p>
                      </div>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => toggleCompare(offer.id)}
                      >
                        <Scale className="h-3.5 w-3.5" />
                        {compareIds.includes(offer.id) ? "Comparing" : "Compare"}
                      </Button>
                      <Button size="sm" onClick={() => void selectOffer(offer)}>
                        Select
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}

            {comparedOffers.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Flight Comparison</CardTitle>
                  <CardDescription>Side-by-side fare and rule breakdown</CardDescription>
                </CardHeader>
                <CardContent className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                        <th className="pb-2 font-medium">Airline</th>
                        <th className="pb-2 font-medium">Price</th>
                        <th className="pb-2 font-medium">Duration</th>
                        <th className="pb-2 font-medium">Baggage</th>
                        <th className="pb-2 font-medium">Refundable</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border)]">
                      {comparedOffers.map((o) => (
                        <tr key={o.id}>
                          <td className="py-2 font-medium">{o.airline}</td>
                          <td className="py-2">${o.priceUsd}</td>
                          <td className="py-2">{o.duration}</td>
                          <td className="py-2">{o.baggage}</td>
                          <td className="py-2">{o.refundable ? "Yes" : "No"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            )}

            {selectedOffer && (
              <Card>
                <CardHeader>
                  <CardTitle>
                    Passenger Details — {selectedOffer.airline} ({selectedOffer.code})
                  </CardTitle>
                  <CardDescription>
                    Selected offer: ${selectedOffer.priceUsd} · {selectedOffer.origin} →{" "}
                    {selectedOffer.destination}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <form
                    onSubmit={handleSubmit(onPassengerSubmit)}
                    className="grid gap-4 sm:grid-cols-2"
                    noValidate
                  >
                    <div className="space-y-1">
                      <label htmlFor="pax-first" className="text-xs font-medium">
                        First Name
                      </label>
                      <Input id="pax-first" placeholder="Amina" {...register("first_name")} />
                      {errors.first_name && (
                        <p className="text-xs text-red-600 dark:text-red-400">
                          {errors.first_name.message}
                        </p>
                      )}
                    </div>
                    <div className="space-y-1">
                      <label htmlFor="pax-last" className="text-xs font-medium">
                        Last Name
                      </label>
                      <Input id="pax-last" placeholder="Rahman" {...register("last_name")} />
                      {errors.last_name && (
                        <p className="text-xs text-red-600 dark:text-red-400">
                          {errors.last_name.message}
                        </p>
                      )}
                    </div>
                    <div className="space-y-1">
                      <label htmlFor="pax-dob" className="text-xs font-medium">
                        Date of Birth
                      </label>
                      <Input id="pax-dob" type="date" {...register("date_of_birth")} />
                      {errors.date_of_birth && (
                        <p className="text-xs text-red-600 dark:text-red-400">
                          {errors.date_of_birth.message}
                        </p>
                      )}
                    </div>
                    <div className="space-y-1">
                      <label htmlFor="pax-nat" className="text-xs font-medium">
                        Nationality (2-letter)
                      </label>
                      <Input id="pax-nat" maxLength={2} {...register("nationality")} />
                      {errors.nationality && (
                        <p className="text-xs text-red-600 dark:text-red-400">
                          {errors.nationality.message}
                        </p>
                      )}
                    </div>
                    <div className="space-y-1">
                      <label htmlFor="pax-passport" className="text-xs font-medium">
                        Passport Number
                      </label>
                      <Input
                        id="pax-passport"
                        placeholder="EA0123456"
                        {...register("passport_number")}
                      />
                      {errors.passport_number && (
                        <p className="text-xs text-red-600 dark:text-red-400">
                          {errors.passport_number.message}
                        </p>
                      )}
                    </div>
                    <div className="space-y-1">
                      <label htmlFor="pax-email" className="text-xs font-medium">
                        Email
                      </label>
                      <Input
                        id="pax-email"
                        type="email"
                        placeholder="amina@example.com"
                        {...register("email")}
                      />
                      {errors.email && (
                        <p className="text-xs text-red-600 dark:text-red-400">
                          {errors.email.message}
                        </p>
                      )}
                    </div>
                    <div className="space-y-1 sm:col-span-2">
                      <label htmlFor="pax-phone" className="text-xs font-medium">
                        Phone Number
                      </label>
                      <Input
                        id="pax-phone"
                        placeholder="+8801700000000"
                        {...register("phone")}
                      />
                      {errors.phone && (
                        <p className="text-xs text-red-600 dark:text-red-400">
                          {errors.phone.message}
                        </p>
                      )}
                    </div>
                    <div className="sm:col-span-2">
                      <Button type="submit" disabled={submittingBooking}>
                        {submittingBooking
                          ? "Creating Reservation..."
                          : selectedOffer.isApiBacked
                            ? "Approve & Create Reservation"
                            : "Validate Passenger & Review Summary"}
                      </Button>
                    </div>
                  </form>

                  {createdBooking && (
                    <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-xs space-y-3">
                      <p className="flex items-center gap-1.5 font-semibold text-emerald-600 dark:text-emerald-400">
                        <CheckCircle2 className="h-4 w-4" />
                        Reservation Created — {createdBooking.booking_reference} (PNR:{" "}
                        {createdBooking.pnr})
                      </p>
                      <p>
                        Status: <strong>{createdBooking.status}</strong> · Total:{" "}
                        {createdBooking.currency} {createdBooking.total_amount} (Service fee:{" "}
                        {createdBooking.service_fee_amount}){" "}
                        {createdBooking.is_sandbox ? "· [Sandbox Reservation]" : ""}
                      </p>

                      {issuedTickets.length === 0 ? (
                        <div className="flex flex-wrap items-center gap-2 pt-1">
                          <select
                            aria-label="Select payment gateway"
                            value={gateway}
                            onChange={(e) =>
                              setGateway(
                                e.target.value as
                                  | "sslcommerz"
                                  | "bkash"
                                  | "nagad"
                                  | "stripe"
                                  | "sandbox"
                              )
                            }
                            className="h-9 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-2.5 text-xs"
                          >
                            <option value="sslcommerz">SSLCommerz (Sandbox)</option>
                            <option value="bkash">bKash (Sandbox)</option>
                            <option value="nagad">Nagad (Sandbox)</option>
                            <option value="stripe">Stripe (Sandbox)</option>
                            <option value="sandbox">Sandbox Gateway</option>
                          </select>
                          <Button
                            size="sm"
                            type="button"
                            disabled={txBusy}
                            onClick={() => void handlePayAndTicket()}
                          >
                            {txBusy
                              ? "Verifying & Issuing..."
                              : "Verify Sandbox Payment & Issue E-Ticket"}
                          </Button>
                        </div>
                      ) : (
                        <div className="space-y-1 border-t border-emerald-500/20 pt-2">
                          <p className="font-semibold">Issued E-Tickets:</p>
                          {issuedTickets.map((t) => (
                            <p key={t.id} className="font-mono">
                              {t.e_ticket_number ?? "Pending"} · {t.status}
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {validatedPassenger && !createdBooking && (
                    <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-xs space-y-2">
                      <p className="flex items-center gap-1.5 font-semibold text-emerald-600 dark:text-emerald-400">
                        <CheckCircle2 className="h-4 w-4" />
                        Booking Summary Ready (Pre-Transaction Preview)
                      </p>
                      <p>
                        Passenger: {validatedPassenger.first_name} {validatedPassenger.last_name} (
                        {validatedPassenger.nationality}) · {selectedOffer.airline}{" "}
                        {selectedOffer.code} (${selectedOffer.priceUsd})
                      </p>
                      <p className="flex items-center gap-1.5 text-[var(--muted-foreground)]">
                        <ShieldAlert className="h-3.5 w-3.5" />
                        Payment gateway execution and e-ticket issuance activate in Phase 7.
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </section>
    </PublicShell>
  );
}
