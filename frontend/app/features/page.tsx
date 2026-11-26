import { Bot, CheckCircle2, Layers, Lock, Plane, Shield } from "lucide-react";
import Link from "next/link";

import { PublicShell } from "@/components/layout/public-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const FEATURE_GROUPS = [
  {
    icon: Bot,
    title: "Multi-Agent LangGraph Supervisor",
    description:
      "14 specialized agents handle intent recognition (English, Bangla, Banglish), slot collection, fare comparison, rules explanation, and human escalation.",
  },
  {
    icon: Plane,
    title: "State-Driven Flight Lifecycle",
    description:
      "Deterministic transitions from REQUESTED through OFFER_SELECTED, PRICE_REVALIDATED, PAYMENT_CONFIRMED, and TICKETED with recovery states.",
  },
  {
    icon: Shield,
    title: "Enterprise Multi-Tenant Security",
    description:
      "PostgreSQL Row-Level Security, Argon2id credentials, rotating refresh tokens, encrypted passport PII, and immutable audit logs.",
  },
  {
    icon: Layers,
    title: "Supplier & Payment Adapters",
    description:
      "Decoupled interfaces supporting Amadeus, Duffel, Sabre, Travelport, SSLCommerz, bKash, Nagad, and Stripe.",
  },
  {
    icon: Lock,
    title: "Zero Hallucination Policy",
    description:
      "AI never invents fares, PNRs, or e-ticket numbers. Transactional actions require validated backend tool execution.",
  },
  {
    icon: CheckCircle2,
    title: "Human-in-the-Loop Workspace",
    description:
      "Travel agents monitor live chats, review AI response suggestions, take over complex cases, and manage refunds or modifications.",
  },
];

export default function FeaturesPage() {
  return (
    <PublicShell>
      <section className="mx-auto max-w-6xl space-y-12 px-4 py-16 sm:px-6">
        <div className="max-w-3xl space-y-4">
          <Badge variant="info">Platform Capabilities</Badge>
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Everything required to run an AI-automated travel agency
          </h1>
          <p className="text-base text-[var(--muted-foreground)]">
            Engineered from the ground up for B2B SaaS reliability, airline transactional safety,
            and regional + global payment readiness.
          </p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURE_GROUPS.map((item) => {
            const Icon = item.icon;
            return (
              <Card key={item.title}>
                <CardHeader>
                  <div className="mb-2 flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--muted)] text-[var(--accent)]">
                    <Icon className="h-5 w-5" />
                  </div>
                  <CardTitle className="text-base">{item.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription>{item.description}</CardDescription>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="flex flex-wrap gap-3">
          <Link href="/register-agency">
            <Button>Onboard Your Agency</Button>
          </Link>
          <Link href="/integrations">
            <Button variant="secondary">Explore Integrations</Button>
          </Link>
        </div>
      </section>
    </PublicShell>
  );
}
