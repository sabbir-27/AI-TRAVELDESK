"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Bot,
  Building2,
  Check,
  ChevronDown,
  Code2,
  Globe,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PublicShell } from "@/components/layout/public-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { saasService } from "@/services/saas-service";

const AGENT_CAPABILITIES = [
  "Intent Recognition (EN / BN / Banglish)",
  "Travel Planning & Slot Filling",
  "Multi-Supplier Flight Search",
  "Transparent Fare Comparison",
  "Fare Rules & Baggage Explainer",
  "Encrypted Passenger Collection",
  "State-Driven Booking & Approval",
  "Verified Payment & E-Ticketing",
  "Changes, Cancellations & Refunds",
  "Human Agent Seamless Handoff",
];

const FAQS = [
  {
    q: "How is each travel agency's data isolated?",
    a: "Every tenant-scoped table enforces an agency_id foreign key backed by PostgreSQL Row-Level Security (RLS). Tenant identity is resolved solely from verified JWT claims or scoped API credentials—never from client-supplied headers.",
  },
  {
    q: "How do agencies integrate AI TravelDesk into an existing website?",
    a: "Agencies can embed the white-label JavaScript chatbot widget with a single script tag, integrate directly via our versioned REST API (/api/v1), or deploy a branded booking portal.",
  },
  {
    q: "Does the AI ever invent flight prices, PNRs, or e-tickets?",
    a: "No. All offers, revalidations, reservations, payments, and e-tickets are executed through deterministic backend state machines and authorized supplier/payment adapters.",
  },
  {
    q: "What languages does the AI Flight Agent support?",
    a: "Customers can converse naturally in English, Bangla, and Banglish with automatic context preservation across human-agent handoffs.",
  },
];

export default function HomePage() {
  const [demoTab, setDemoTab] = useState<"ai" | "widget" | "api">("ai");
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  const plansQuery = useQuery({
    queryKey: ["public", "plans"],
    queryFn: () => saasService.listPublicPlans(),
    retry: false,
  });

  return (
    <PublicShell>
      {/* Hero */}
      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          className="grid items-center gap-12 lg:grid-cols-12"
        >
          <div className="space-y-6 lg:col-span-7">
            <Badge variant="info">Enterprise Multi-Tenant Travel SaaS</Badge>
            <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
              Automate flight search, booking, and support for every travel agency.
            </h1>
            <p className="text-lg leading-relaxed text-[var(--muted-foreground)]">
              AI TravelDesk gives independent travel agencies a white-label LangGraph AI Flight
              Agent, supplier-agnostic booking workflows, and a unified human-agent workspace—all
              on an isolated B2B SaaS core.
            </p>
            <div className="flex flex-wrap gap-3 pt-1">
              <Link href="/register-agency">
                <Button size="lg">
                  Onboard Your Agency
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/book">
                <Button variant="secondary" size="lg">
                  Explore Booking UI
                </Button>
              </Link>
            </div>
          </div>

          {/* Interactive Product Demonstration */}
          <Card className="lg:col-span-5">
            <CardHeader className="border-b border-[var(--border)] pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold">Platform Demonstration</CardTitle>
                <div className="flex gap-1 rounded-lg bg-[var(--muted)] p-1 text-xs">
                  {(["ai", "widget", "api"] as const).map((tab) => (
                    <button
                      key={tab}
                      type="button"
                      onClick={() => setDemoTab(tab)}
                      className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                        demoTab === tab
                          ? "bg-[var(--surface)] text-[var(--foreground)] shadow-xs"
                          : "text-[var(--muted-foreground)]"
                      }`}
                    >
                      {tab === "ai" ? "AI Agent" : tab === "widget" ? "Widget" : "REST API"}
                    </button>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-4">
              {demoTab === "ai" && (
                <div className="space-y-3 text-xs">
                  <div className="rounded-lg bg-[var(--muted)] p-3">
                    <p className="font-medium">Customer (Banglish)</p>
                    <p className="mt-1 text-[var(--muted-foreground)]">
                      &ldquo;Dhaka theke Dubai 15 Dec 2 jon adult economy flight dekhaw.&rdquo;
                    </p>
                  </div>
                  <div className="rounded-lg border border-[var(--border)] p-3">
                    <p className="flex items-center gap-1.5 font-medium text-[var(--accent)]">
                      <Sparkles className="h-3.5 w-3.5" />
                      AI Travel Consultant
                    </p>
                    <p className="mt-1 text-[var(--muted-foreground)]">
                      Routing to Flight Search &amp; Fare Rules agents for DAC → DXB (2 ADT,
                      Economy). Live offers, baggage rules, and total fare breakdown will be
                      validated via supplier adapters before reservation.
                    </p>
                  </div>
                </div>
              )}

              {demoTab === "widget" && (
                <pre className="overflow-x-auto rounded-lg bg-[var(--muted)] p-3 text-xs leading-relaxed">
                  {`<script\n  src="https://platform.example.com/widget.js"\n  data-agency-id="AGENCY_ID"\n  data-widget-token="SCOPED_PUBLIC_TOKEN"\n></script>`}
                </pre>
              )}

              {demoTab === "api" && (
                <pre className="overflow-x-auto rounded-lg bg-[var(--muted)] p-3 text-xs leading-relaxed">
                  {`POST /api/v1/flights/search\nPOST /api/v1/flights/price\nPOST /api/v1/bookings\nPOST /api/v1/agent/conversations`}
                </pre>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </section>

      {/* Core Pillars */}
      <section className="border-t border-[var(--border)] bg-[var(--surface)] py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="max-w-2xl space-y-2">
            <h2 className="text-2xl font-semibold tracking-tight">
              Built for multi-tenant scale and deterministic travel operations
            </h2>
            <p className="text-sm text-[var(--muted-foreground)]">
              Every agency receives isolated customer records, branded AI assistants, and full
              booking lifecycle traceability.
            </p>
          </div>

          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                icon: ShieldCheck,
                title: "Zero-Trust Multi-Tenancy",
                desc: "PostgreSQL RLS and verified JWT tenant resolution protect every agency boundary.",
              },
              {
                icon: Bot,
                title: "14 Specialized AI Agents",
                desc: "LangGraph supervisor orchestrates search, comparison, fare rules, and handoff.",
              },
              {
                icon: Workflow,
                title: "Adapter Architecture",
                desc: "Decoupled interfaces for Amadeus, Duffel, Sabre, SSLCommerz, bKash, and Stripe.",
              },
              {
                icon: Building2,
                title: "Human Agent Workspace",
                desc: "Seamless escalation inbox with AI suggestions, internal notes, and takeover.",
              },
            ].map((item) => {
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
                    <CardDescription>{item.desc}</CardDescription>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* AI Multi-Agent Highlights & Integration Methods */}
      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="grid gap-10 lg:grid-cols-2">
          <div className="space-y-4">
            <Badge>LangGraph Orchestration</Badge>
            <h2 className="text-2xl font-semibold tracking-tight">
              AI Flight Consultant with Strict Safety Guardrails
            </h2>
            <p className="text-sm text-[var(--muted-foreground)]">
              Transactional actions are executed exclusively via validated backend tools with
              explicit customer approval and idempotency keys.
            </p>
            <ul className="grid gap-2 pt-2 sm:grid-cols-2 text-sm">
              {AGENT_CAPABILITIES.map((cap) => (
                <li key={cap} className="flex items-center gap-2">
                  <Check className="h-4 w-4 shrink-0 text-emerald-500" />
                  <span>{cap}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="grid gap-4">
            {[
              {
                icon: Globe,
                title: "1. JavaScript Chatbot Widget",
                desc: "Floating responsive chat widget customized with your agency logo, colors, welcome message, and scoped public token.",
              },
              {
                icon: Code2,
                title: "2. Versioned REST API",
                desc: "OpenAPI-documented endpoints for flight search, pricing, booking lifecycle, and conversational AI.",
              },
              {
                icon: Building2,
                title: "3. White-Label Booking Portal",
                desc: "Branded end-to-end flight search, fare comparison, passenger collection, and e-ticket portal.",
              },
            ].map((method) => {
              const Icon = method.icon;
              return (
                <Card key={method.title}>
                  <CardHeader className="flex flex-row items-start gap-3 space-y-0">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--muted)] text-[var(--accent)]">
                      <Icon className="h-4 w-4" />
                    </div>
                    <div>
                      <CardTitle className="text-base">{method.title}</CardTitle>
                      <CardDescription className="mt-1">{method.desc}</CardDescription>
                    </div>
                  </CardHeader>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* Pricing Plans */}
      <section className="border-t border-[var(--border)] bg-[var(--surface)] py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">Transparent SaaS Pricing</h2>
              <p className="text-sm text-[var(--muted-foreground)]">
                Scale from independent agency to high-volume enterprise consolidator.
              </p>
            </div>
            <Link href="/pricing">
              <Button variant="secondary" size="sm">
                Compare Full Plans
              </Button>
            </Link>
          </div>

          <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {(plansQuery.data && plansQuery.data.length > 0
              ? plansQuery.data
              : [
                  {
                    id: "starter",
                    tier: "STARTER",
                    name: "Starter",
                    monthly_price_usd: "49.00",
                    annual_price_usd: "470.00",
                    monthly_api_limit: 10000,
                    monthly_conversation_limit: 1000,
                    monthly_booking_limit: 150,
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
                  },
                ]
            ).map((plan) => (
              <Card key={plan.id} className="flex flex-col justify-between">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">{plan.name}</CardTitle>
                    <Badge>{plan.tier}</Badge>
                  </div>
                  <p className="pt-2 text-2xl font-semibold">${plan.monthly_price_usd}/mo</p>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ul className="space-y-1.5 text-xs text-[var(--muted-foreground)]">
                    <li>{plan.monthly_api_limit.toLocaleString()} API requests/mo</li>
                    <li>{plan.monthly_conversation_limit.toLocaleString()} AI chats/mo</li>
                    <li>{plan.monthly_booking_limit.toLocaleString()} bookings/mo</li>
                  </ul>
                  <Link href="/register-agency" className="block">
                    <Button variant="secondary" size="sm" className="w-full">
                      Start with {plan.name}
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ + CTA */}
      <section className="mx-auto max-w-4xl px-4 py-16 sm:px-6">
        <h2 className="text-center text-2xl font-semibold tracking-tight">
          Frequently Asked Questions
        </h2>
        <div className="mt-8 space-y-3">
          {FAQS.map((item, idx) => (
            <div
              key={item.q}
              className="rounded-xl border border-[var(--border)] bg-[var(--surface)]"
            >
              <button
                type="button"
                onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                className="flex w-full items-center justify-between px-5 py-4 text-left text-sm font-medium"
              >
                <span>{item.q}</span>
                <ChevronDown
                  className={`h-4 w-4 transition-transform ${openFaq === idx ? "rotate-180" : ""}`}
                />
              </button>
              {openFaq === idx && (
                <div className="border-t border-[var(--border)] px-5 py-3 text-sm text-[var(--muted-foreground)]">
                  {item.a}
                </div>
              )}
            </div>
          ))}
        </div>

        <Card className="mt-14 bg-[var(--surface)]">
          <CardContent className="flex flex-col items-center justify-between gap-4 p-8 text-center sm:flex-row sm:text-left">
            <div>
              <h3 className="text-lg font-semibold">Ready to launch your AI travel desk?</h3>
              <p className="text-sm text-[var(--muted-foreground)]">
                Onboard your agency in minutes and configure your white-label workspace.
              </p>
            </div>
            <Link href="/register-agency">
              <Button size="lg">Register Agency</Button>
            </Link>
          </CardContent>
        </Card>
      </section>
    </PublicShell>
  );
}
