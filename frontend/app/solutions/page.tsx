import { Building, Globe2, Headphones, Sparkles } from "lucide-react";
import Link from "next/link";

import { PublicShell } from "@/components/layout/public-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const SOLUTIONS = [
  {
    icon: Building,
    title: "Independent Retail Travel Agencies",
    description:
      "Embed a 24/7 multilingual AI flight agent on your existing site without hiring an engineering team.",
  },
  {
    icon: Globe2,
    title: "Regional OTAs & Consolidators",
    description:
      "Connect Amadeus/Duffel inventories alongside SSLCommerz, bKash, Nagad, and Stripe via unified REST APIs.",
  },
  {
    icon: Headphones,
    title: "Hybrid AI + Human Operations",
    description:
      "Automate routine fare inquiries while routing schedule disruptions, visa checks, and refunds to your travel consultants.",
  },
  {
    icon: Sparkles,
    title: "Corporate Travel Desks",
    description:
      "Enforce agency service fees, role-based approvals, and complete audit logging across every reservation.",
  },
];

export default function SolutionsPage() {
  return (
    <PublicShell>
      <section className="mx-auto max-w-6xl space-y-10 px-4 py-16 sm:px-6">
        <div className="max-w-2xl space-y-4">
          <Badge variant="info">Industry Solutions</Badge>
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Tailored workflows for every travel business model
          </h1>
          <p className="text-base text-[var(--muted-foreground)]">
            Whether you operate a boutique agency or a multi-branch consolidator, AI TravelDesk
            adapts to your suppliers, currencies, and team roles.
          </p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2">
          {SOLUTIONS.map((sol) => {
            const Icon = sol.icon;
            return (
              <Card key={sol.title}>
                <CardHeader>
                  <div className="mb-2 flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--muted)] text-[var(--accent)]">
                    <Icon className="h-5 w-5" />
                  </div>
                  <CardTitle className="text-lg">{sol.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription>{sol.description}</CardDescription>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <Link href="/register-agency">
          <Button>Get Started as an Agency</Button>
        </Link>
      </section>
    </PublicShell>
  );
}
