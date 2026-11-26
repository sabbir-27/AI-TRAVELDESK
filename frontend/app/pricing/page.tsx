"use client";

import { useQuery } from "@tanstack/react-query";
import { Check } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PublicShell } from "@/components/layout/public-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { saasService } from "@/services/saas-service";

export default function PricingPage() {
  const [annual, setAnnual] = useState(false);

  const plansQuery = useQuery({
    queryKey: ["public", "plans"],
    queryFn: () => saasService.listPublicPlans(),
    retry: false,
  });

  const fallbackPlans = [
    {
      id: "starter",
      tier: "STARTER",
      name: "Starter",
      monthly_price_usd: "49.00",
      annual_price_usd: "470.00",
      monthly_api_limit: 10000,
      monthly_conversation_limit: 1000,
      monthly_booking_limit: 150,
      overage_per_booking_usd: "1.50",
    },
    {
      id: "professional",
      tier: "PROFESSIONAL",
      name: "Professional",
      monthly_price_usd: "149.00",
      annual_price_usd: "1430.00",
      monthly_api_limit: 50000,
      monthly_conversation_limit: 5000,
      monthly_booking_limit: 750,
      overage_per_booking_usd: "1.00",
    },
    {
      id: "business",
      tier: "BUSINESS",
      name: "Business",
      monthly_price_usd: "399.00",
      annual_price_usd: "3830.00",
      monthly_api_limit: 250000,
      monthly_conversation_limit: 25000,
      monthly_booking_limit: 3000,
      overage_per_booking_usd: "0.65",
    },
    {
      id: "enterprise",
      tier: "ENTERPRISE",
      name: "Enterprise",
      monthly_price_usd: "999.00",
      annual_price_usd: "9590.00",
      monthly_api_limit: 1000000,
      monthly_conversation_limit: 150000,
      monthly_booking_limit: 20000,
      overage_per_booking_usd: "0.35",
    },
  ];

  const plans = plansQuery.data && plansQuery.data.length > 0 ? plansQuery.data : fallbackPlans;

  return (
    <PublicShell>
      <section className="mx-auto max-w-6xl space-y-10 px-4 py-16 sm:px-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="space-y-3">
            <Badge variant="info">Subscription Tiers</Badge>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              Simple, predictable SaaS pricing
            </h1>
            <p className="text-sm text-[var(--muted-foreground)]">
              Every plan includes multi-tenant isolation, RBAC, and OpenAPI access.
            </p>
          </div>

          <div className="inline-flex rounded-lg border border-[var(--border)] bg-[var(--surface)] p-1 text-sm">
            <button
              type="button"
              onClick={() => setAnnual(false)}
              className={`rounded-md px-3 py-1.5 font-medium ${
                !annual ? "bg-[var(--accent)] text-[var(--accent-foreground)]" : ""
              }`}
            >
              Monthly
            </button>
            <button
              type="button"
              onClick={() => setAnnual(true)}
              className={`rounded-md px-3 py-1.5 font-medium ${
                annual ? "bg-[var(--accent)] text-[var(--accent-foreground)]" : ""
              }`}
            >
              Annual (Save 20%)
            </button>
          </div>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {plans.map((plan) => (
            <Card key={plan.id} className="flex flex-col justify-between">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{plan.name}</CardTitle>
                  <Badge>{plan.tier}</Badge>
                </div>
                <CardDescription className="pt-2">
                  <span className="text-3xl font-semibold text-[var(--foreground)]">
                    ${annual ? plan.annual_price_usd : plan.monthly_price_usd}
                  </span>
                  <span>/{annual ? "yr" : "mo"}</span>
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                <ul className="space-y-2 text-xs text-[var(--muted-foreground)]">
                  <li className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-emerald-500" />
                    {plan.monthly_api_limit.toLocaleString()} API requests / mo
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-emerald-500" />
                    {plan.monthly_conversation_limit.toLocaleString()} AI chats / mo
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-emerald-500" />
                    {plan.monthly_booking_limit.toLocaleString()} bookings / mo
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-emerald-500" />
                    ${plan.overage_per_booking_usd} per extra booking
                  </li>
                </ul>
                <Link href="/register-agency" className="block">
                  <Button className="w-full" size="sm">
                    Choose {plan.name}
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    </PublicShell>
  );
}
