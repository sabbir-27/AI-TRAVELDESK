import { PublicShell } from "@/components/layout/public-shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AboutPage() {
  return (
    <PublicShell>
      <section className="mx-auto max-w-4xl space-y-8 px-4 py-16 sm:px-6">
        <div className="space-y-3">
          <Badge variant="info">About AI TravelDesk</Badge>
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Enterprise travel infrastructure built for modern agencies
          </h1>
          <p className="text-base leading-relaxed text-[var(--muted-foreground)]">
            AI TravelDesk bridges conversational AI and deterministic airline distribution. Our
            platform empowers independent travel agencies to offer responsive, 24/7 booking
            automation without compromising tenant security, supplier flexibility, or financial
            auditability.
          </p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Engineering Principles</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-[var(--muted-foreground)]">
              API-first architecture, PostgreSQL Row-Level Security, strict Pydantic v2 contracts,
              and state-machine-enforced booking lifecycles.
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Global + Regional Readiness</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-[var(--muted-foreground)]">
              Built to support both global GDS/NDC airlines and South Asian payment ecosystems
              (bKash, Nagad, SSLCommerz) alongside Stripe.
            </CardContent>
          </Card>
        </div>
      </section>
    </PublicShell>
  );
}
