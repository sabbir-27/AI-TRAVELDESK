import { Code2, Globe, Palette } from "lucide-react";

import { PublicShell } from "@/components/layout/public-shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function IntegrationsPage() {
  return (
    <PublicShell>
      <section className="mx-auto max-w-6xl space-y-10 px-4 py-16 sm:px-6">
        <div className="max-w-3xl space-y-3">
          <Badge variant="info">Integration Methods</Badge>
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Three ways to connect AI TravelDesk to your agency
          </h1>
          <p className="text-base text-[var(--muted-foreground)]">
            Embed our JavaScript chatbot widget, call our versioned OpenAPI endpoints directly, or
            launch a white-label customer booking experience.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <Globe className="mb-2 h-6 w-6 text-[var(--accent)]" />
              <CardTitle>JavaScript Widget</CardTitle>
              <CardDescription>Drop-in floating assistant with origin-bound token.</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="overflow-x-auto rounded-lg bg-[var(--muted)] p-3 text-xs">
                {`<script\n  src="https://platform.example.com/widget.js"\n  data-agency-id="AGENCY_ID"\n></script>`}
              </pre>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <Code2 className="mb-2 h-6 w-6 text-[var(--accent)]" />
              <CardTitle>Versioned REST API</CardTitle>
              <CardDescription>Server-to-server endpoints authenticated via API key.</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="overflow-x-auto rounded-lg bg-[var(--muted)] p-3 text-xs">
                {`POST /api/v1/flights/search\nPOST /api/v1/flights/price\nPOST /api/v1/bookings\nPOST /api/v1/agent/conversations`}
              </pre>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <Palette className="mb-2 h-6 w-6 text-[var(--accent)]" />
              <CardTitle>White-Label Portal</CardTitle>
              <CardDescription>
                Customize logo, colors, AI persona, languages, and agency service fees.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-[var(--muted-foreground)]">
              Travelers interact exclusively with your agency identity throughout search, booking,
              payment, and ticket delivery.
            </CardContent>
          </Card>
        </div>
      </section>
    </PublicShell>
  );
}
