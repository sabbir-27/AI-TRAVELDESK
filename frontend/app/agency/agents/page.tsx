"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowUpRight,
  Bot,
  CheckCircle2,
  Cpu,
  Globe,
  Headset,
  Luggage,
  Plane,
  RefreshCw,
  Send,
  Settings2,
  ShieldCheck,
  Sparkles,
  UserCheck,
} from "lucide-react";
import Link from "next/link";
import React, { useEffect, useRef, useState } from "react";

import { FormattedChatText } from "@/components/chat/formatted-chat-text";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api-client";
import { saasService } from "@/services/saas-service";
import type { AgentMessage, AgentTurnResponse } from "@/types/saas";

const LANGUAGE_OPTIONS = [
  { code: "en", label: "English" },
  { code: "bn", label: "বাংলা (Bangla)" },
  { code: "banglish", label: "Banglish" },
] as const;

const WORKFLOW_STEPS = [
  { key: "COLLECTING_REQUIREMENTS", label: "1. Itinerary" },
  { key: "FLIGHTS_FOUND", label: "2. Flight Search" },
  { key: "FLIGHT_SELECTION", label: "3. Selection" },
  { key: "COLLECTING_PASSENGERS", label: "4. Passengers" },
  { key: "BOOKING_REVIEW", label: "5. Review" },
  { key: "PAYMENT_PENDING", label: "6. Reserved" },
] as const;

const STEP_ORDER: Record<string, number> = {
  COLLECTING_REQUIREMENTS: 0,
  READY_FOR_FLIGHT_SEARCH: 1,
  SEARCHING_FLIGHTS: 1,
  FLIGHTS_FOUND: 1,
  FLIGHT_SELECTION: 2,
  COLLECTING_PASSENGERS: 3,
  VALIDATING_INFORMATION: 3,
  BOOKING_REVIEW: 4,
  PAYMENT_PENDING: 5,
  BOOKING_CONFIRMED: 5,
};

const QUICK_SCENARIOS = [
  {
    label: "Dhaka → Dubai Tomorrow",
    prompt: "I need a flight from Dhaka to Dubai tomorrow for 1 adult in economy",
  },
  {
    label: "Dhaka → Berlin (15 Dec)",
    prompt: "I want to fly from Dhaka to Berlin on 15 December 2026 for 1 adult",
  },
  {
    label: "Banglish Query",
    prompt: "Dhaka theke Dubai kal 2 jon economy flight dekhaw",
  },
  {
    label: "Change to London",
    prompt: "Change destination to London",
  },
  {
    label: "Talk to Human",
    prompt: "Please connect me to a human travel consultant",
  },
] as const;

interface EmbeddedOffer {
  offer_id?: string;
  airline?: string;
  flight_number?: string;
  origin?: string;
  destination?: string;
  departure_time?: string;
  arrival_time?: string;
  duration?: string;
  stops?: number;
  baggage?: string;
  refundable?: boolean;
  total_fare?: number;
  currency?: string;
  is_sandbox?: boolean;
}

function AgencyAgentsContent() {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  const configQuery = useQuery({
    queryKey: ["agency", "agent-config"],
    queryFn: () => saasService.getAgentConfig(),
  });

  const [activeTab, setActiveTab] = useState<"console" | "config">("console");
  const [agentName, setAgentName] = useState("Aria Travel Consultant");
  const [welcomeMessage, setWelcomeMessage] = useState("");
  const [tone, setTone] = useState("professional");
  const [handoffThreshold, setHandoffThreshold] = useState("3");
  const [supportedLanguages, setSupportedLanguages] = useState<string[]>([
    "en",
    "bn",
    "banglish",
  ]);
  const [customInstructions, setCustomInstructions] = useState("");
  const [isActive, setIsActive] = useState(true);

  const [conversationId, setConversationId] = useState<string | null>(null);
  const [convStatus, setConvStatus] = useState<string>("AI_ACTIVE");
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [lastMeta, setLastMeta] = useState<AgentTurnResponse | null>(null);
  const [draft, setDraft] = useState("");
  const [showRawJson, setShowRawJson] = useState(false);

  useEffect(() => {
    if (configQuery.data) {
      setAgentName(configQuery.data.agent_name);
      setWelcomeMessage(configQuery.data.welcome_message);
      setTone(configQuery.data.tone);
      setHandoffThreshold(String(configQuery.data.auto_handoff_threshold));
      setSupportedLanguages(
        configQuery.data.supported_languages?.length
          ? configQuery.data.supported_languages
          : ["en", "bn", "banglish"]
      );
      setCustomInstructions(configQuery.data.custom_instructions ?? "");
      setIsActive(configQuery.data.is_active);
    }
  }, [configQuery.data]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const toggleLanguage = (code: string) => {
    setSupportedLanguages((prev) => {
      if (prev.includes(code)) {
        return prev.length > 1 ? prev.filter((item) => item !== code) : prev;
      }
      return [...prev, code];
    });
  };

  const saveConfigMutation = useMutation({
    mutationFn: () =>
      saasService.updateAgentConfig({
        agent_name: agentName.trim(),
        welcome_message: welcomeMessage.trim(),
        tone,
        auto_handoff_threshold: Number(handoffThreshold) || 3,
        supported_languages: supportedLanguages,
        custom_instructions: customInstructions.trim(),
        is_active: isActive,
      }),
    onSuccess: () => {
      pushToast({ variant: "success", title: "AI consultant configuration saved" });
      void queryClient.invalidateQueries({ queryKey: ["agency", "agent-config"] });
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Save failed",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  const startChatMutation = useMutation({
    mutationFn: () => saasService.createAgentConversation("SANDBOX_CONSOLE"),
    onSuccess: (conv) => {
      setConversationId(conv.id);
      setConvStatus(conv.status);
      setMessages(conv.messages);
      setLastMeta(null);
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Unable to start AI session",
        description: err instanceof ApiError ? err.detail : "Agency must be ACTIVE",
      });
    },
  });

  const sendMessageMutation = useMutation({
    mutationFn: async (text: string) => {
      let cid = conversationId;
      if (!cid) {
        const created = await saasService.createAgentConversation("SANDBOX_CONSOLE");
        cid = created.id;
        setConversationId(cid);
        setConvStatus(created.status);
        setMessages(created.messages);
      }
      return saasService.sendAgentMessage(cid, text);
    },
    onSuccess: (turn) => {
      setConvStatus(turn.status);
      setMessages((prev) => [...prev, turn.customer_message, turn.agent_message]);
      setLastMeta(turn);
      setDraft("");
    },
    onError: (err) => {
      pushToast({
        variant: "error",
        title: "Message failed",
        description: err instanceof ApiError ? err.detail : "Unexpected error",
      });
    },
  });

  const submitMessage = (text: string) => {
    const clean = text.trim();
    if (!clean || sendMessageMutation.isPending) return;
    sendMessageMutation.mutate(clean);
  };

  const bookingState = (lastMeta?.booking_state || {}) as Record<string, unknown>;
  const currentStage = String(bookingState.booking_status || "COLLECTING_REQUIREMENTS");
  const activeStepIdx = STEP_ORDER[currentStage] ?? 0;

  // Dynamic context-aware quick suggestions for frictionless user testing
  const contextualChips = (() => {
    switch (currentStage) {
      case "FLIGHTS_FOUND":
        return [
          { label: "Compare options", prompt: "Compare these flight options" },
          { label: "Select Emirates", prompt: "Select Emirates" },
          { label: "Select Qatar Airways", prompt: "Select Qatar Airways" },
          { label: "Emirates rules", prompt: "What are the fare rules for Emirates?" },
        ];
      case "COLLECTING_PASSENGERS":
        return [
          {
            label: "Submit Sample Passenger",
            prompt:
              "Name: Tariqul Islam, DOB: 1991-03-10, Nationality: BD, Passport: BZ5544332, Email: tariq@example.com, Phone: +8801711111111",
          },
        ];
      case "VALIDATING_INFORMATION":
        return [{ label: "Proceed to Booking Review", prompt: "Proceed" }];
      case "BOOKING_REVIEW":
        return [
          { label: "Confirm & Reserve", prompt: "Confirm" },
          { label: "Change destination to London", prompt: "Change destination to London" },
        ];
      default:
        return QUICK_SCENARIOS.map((s) => ({ label: s.label, prompt: s.prompt }));
    }
  })();

  return (
    <DashboardShell
      portal="agency"
      title="AI Flight Consultant Chatbot"
      subtitle="Enterprise LangGraph multi-agent consultant with persistent booking state and live supplier tools"
    >
      {/* Top Studio Header & Mode Switcher */}
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={isActive ? "success" : "warning"}>
            {isActive ? "Consultant Active" : "Consultant Paused"}
          </Badge>
          <Badge variant="info">
            <Cpu className="mr-1 h-3 w-3" />
            LangGraph 14-Node
          </Badge>
          <Badge>
            <ShieldCheck className="mr-1 h-3 w-3 text-emerald-500" />
            Anti-Hallucination Guard
          </Badge>
          {lastMeta?.llm_provider && (
            <Badge variant="success">{lastMeta.llm_provider}</Badge>
          )}
        </div>

        <div className="inline-flex rounded-lg border border-[var(--border)] bg-[var(--surface)] p-1 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab("console")}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition ${
              activeTab === "console"
                ? "bg-[var(--accent)] text-[var(--accent-foreground)]"
                : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            }`}
          >
            <Sparkles className="h-3.5 w-3.5" />
            Live Consultant Chat
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("config")}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition ${
              activeTab === "config"
                ? "bg-[var(--accent)] text-[var(--accent-foreground)]"
                : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            }`}
          >
            <Settings2 className="h-3.5 w-3.5" />
            Persona &amp; Guardrails
          </button>
        </div>
      </div>

      {activeTab === "console" ? (
        <div className="grid gap-6 lg:grid-cols-12">
          {/* Primary Chat Workspace (8 cols) */}
          <Card className="lg:col-span-8 flex flex-col">
            {/* Session Header + Workflow Stepper */}
            <CardHeader className="space-y-3 border-b border-[var(--border)] pb-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--accent)]/15 text-[var(--accent)]">
                    <Bot className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="text-base">{agentName}</CardTitle>
                    <CardDescription className="text-xs">
                      Continuous conversation memory · English, বাংলা &amp; Banglish
                    </CardDescription>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {conversationId && (
                    <Badge variant={convStatus === "HUMAN_HANDOFF" ? "warning" : "success"}>
                      {convStatus}
                    </Badge>
                  )}
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => startChatMutation.mutate()}
                    disabled={startChatMutation.isPending}
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    New Session
                  </Button>
                </div>
              </div>

              {/* 6-Stage Booking Workflow Stepper */}
              <div className="grid grid-cols-3 gap-1.5 sm:grid-cols-6">
                {WORKFLOW_STEPS.map((step, idx) => {
                  const done = idx < activeStepIdx;
                  const active = idx === activeStepIdx;
                  return (
                    <div
                      key={step.key}
                      className={`rounded-md border px-2 py-1 text-center text-[10px] font-medium transition ${
                        active
                          ? "border-[var(--accent)] bg-[var(--accent)]/15 text-[var(--accent)]"
                          : done
                          ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-500"
                          : "border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)]"
                      }`}
                    >
                      {step.label}
                    </div>
                  );
                })}
              </div>
            </CardHeader>

            <CardContent className="flex flex-1 flex-col gap-3 pt-4">
              {lastMeta?.requires_human_handoff && conversationId && (
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs">
                  <span className="font-medium text-amber-400">
                    Conversation escalated to human travel consultant queue.
                  </span>
                  <Link
                    href={`/workspace/conversations/${conversationId}`}
                    className="inline-flex items-center gap-1 font-semibold text-amber-400 hover:underline"
                  >
                    <Headset className="h-3.5 w-3.5" />
                    Open in Agent Inbox
                    <ArrowUpRight className="h-3 w-3" />
                  </Link>
                </div>
              )}

              {/* Conversation Thread */}
              <div className="h-[460px] space-y-3 overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--background)] p-4 text-sm">
                {messages.length === 0 ? (
                  <div className="flex h-full flex-col items-center justify-center text-center px-6">
                    <div className="mb-3 rounded-full bg-[var(--accent)]/15 p-3 text-[var(--accent)]">
                      <Plane className="h-6 w-6" />
                    </div>
                    <p className="text-sm font-semibold">Ready to plan or book your trip</p>
                    <p className="mt-1 max-w-md text-xs text-[var(--muted-foreground)]">
                      Try partial inputs like &ldquo;From Dhaka on 2026-12-15&rdquo; followed by
                      &ldquo;Berlin&rdquo;, or pick a quick scenario below.
                    </p>
                  </div>
                ) : (
                  messages.map((msg) => {
                    const meta = msg.tool_metadata || {};
                    const embeddedOffers = Array.isArray(meta.flight_offers)
                      ? (meta.flight_offers as EmbeddedOffer[])
                      : [];
                    const embeddedRules =
                      meta.fare_rules_summary && typeof meta.fare_rules_summary === "object"
                        ? (meta.fare_rules_summary as Record<string, unknown>)
                        : null;
                    const embeddedSummary =
                      meta.booking_summary && typeof meta.booking_summary === "object"
                        ? (meta.booking_summary as Record<string, unknown>)
                        : null;
                    const embeddedRecord =
                      meta.booking_record && typeof meta.booking_record === "object"
                        ? (meta.booking_record as Record<string, unknown>)
                        : null;

                    const isCustomer = msg.sender_type === "CUSTOMER";

                    return (
                      <div
                        key={msg.id}
                        className={`flex flex-col ${isCustomer ? "items-end" : "items-start"}`}
                      >
                        <div
                          className={`max-w-[92%] rounded-xl px-4 py-3 text-xs ${
                            isCustomer
                              ? "bg-[var(--accent)] text-[var(--accent-foreground)]"
                              : "w-full border border-[var(--border)] bg-[var(--surface)]"
                          }`}
                        >
                          <div className="mb-1.5 flex items-center justify-between gap-3 text-[10px] font-semibold opacity-75">
                            <span>{isCustomer ? "You" : agentName}</span>
                            {typeof meta.active_agent === "string" && (
                              <span>{meta.active_agent}</span>
                            )}
                          </div>

                          <FormattedChatText content={msg.content} />

                          {/* Interactive Flight Offer Cards */}
                          {embeddedOffers.length > 0 && (
                            <div className="mt-3 grid gap-2.5 sm:grid-cols-3">
                              {embeddedOffers.map((offer, idx) => (
                                <div
                                  key={`${offer.flight_number || idx}`}
                                  className="flex flex-col justify-between rounded-lg border border-[var(--border)] bg-[var(--background)] p-3 text-[11px]"
                                >
                                  <div>
                                    <div className="flex items-center justify-between gap-1 font-semibold">
                                      <span className="truncate">{offer.airline}</span>
                                      <span className="text-[var(--accent)]">
                                        ${offer.total_fare}
                                      </span>
                                    </div>
                                    <p className="mt-0.5 text-[10px] text-[var(--muted-foreground)]">
                                      {offer.flight_number} · {offer.origin} {offer.departure_time}{" "}
                                      → {offer.destination} {offer.arrival_time}
                                    </p>
                                    <div className="mt-1.5 flex flex-wrap gap-1 text-[10px]">
                                      <span className="rounded bg-[var(--surface)] px-1.5 py-0.5 border border-[var(--border)]">
                                        {offer.stops === 0 ? "Direct" : `${offer.stops} stop`} (
                                        {offer.duration})
                                      </span>
                                      {offer.baggage && (
                                        <span className="inline-flex items-center gap-0.5 rounded bg-[var(--surface)] px-1.5 py-0.5 border border-[var(--border)]">
                                          <Luggage className="h-2.5 w-2.5" />
                                          {offer.baggage.split("+")[0].trim()}
                                        </span>
                                      )}
                                      <span
                                        className={`rounded px-1.5 py-0.5 border ${
                                          offer.refundable
                                            ? "border-emerald-500/40 text-emerald-500"
                                            : "border-[var(--border)] text-[var(--muted-foreground)]"
                                        }`}
                                      >
                                        {offer.refundable ? "Refundable" : "Saver"}
                                      </span>
                                    </div>
                                  </div>

                                  <div className="mt-2.5 flex items-center justify-between border-t border-[var(--border)] pt-2">
                                    <button
                                      type="button"
                                      onClick={() => submitMessage(`Select ${offer.airline}`)}
                                      className="font-semibold text-emerald-500 hover:underline"
                                    >
                                      Select flight
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() =>
                                        submitMessage(
                                          `What are the fare rules for ${offer.airline}?`
                                        )
                                      }
                                      className="text-[var(--accent)] hover:underline"
                                    >
                                      Fare rules
                                    </button>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Fare Rules Structured Card */}
                          {embeddedRules && (
                            <div className="mt-3 rounded-lg border border-[var(--border)] bg-[var(--background)] p-3 text-[11px]">
                              <p className="font-semibold">
                                {String(embeddedRules.airline)} (
                                {String(embeddedRules.flight_number)}) —{" "}
                                {String(embeddedRules.fare_type)}
                              </p>
                              <div className="mt-1 grid grid-cols-2 gap-1 text-[10px] text-[var(--muted-foreground)]">
                                <span>
                                  Change Fee: ${String(embeddedRules.change_penalty_usd)} USD
                                </span>
                                <span>
                                  Cancel Fee: ${String(embeddedRules.cancellation_penalty_usd)} USD
                                </span>
                                <span>Baggage: {String(embeddedRules.baggage_allowance)}</span>
                                <span>Seats: {String(embeddedRules.seat_selection)}</span>
                              </div>
                            </div>
                          )}

                          {/* Interactive Booking Review Card */}
                          {embeddedSummary && !embeddedRecord && (
                            <div className="mt-3 rounded-lg border border-[var(--accent)]/40 bg-[var(--accent)]/5 p-3 text-[11px]">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <div>
                                  <p className="font-semibold">
                                    {String(embeddedSummary.airline)} (
                                    {String(embeddedSummary.flight_number)}) ·{" "}
                                    {String(embeddedSummary.route)}
                                  </p>
                                  <p className="text-[10px] text-[var(--muted-foreground)]">
                                    Departure: {String(embeddedSummary.departure_date)} · Total: $
                                    {String(embeddedSummary.total_amount_usd)} USD
                                  </p>
                                </div>
                                <Button
                                  size="sm"
                                  onClick={() => submitMessage("Confirm")}
                                  disabled={sendMessageMutation.isPending}
                                >
                                  <UserCheck className="h-3.5 w-3.5" />
                                  Approve &amp; Reserve
                                </Button>
                              </div>
                            </div>
                          )}

                          {/* Real Persisted Reservation Confirmation Card */}
                          {embeddedRecord && (
                            <div className="mt-3 rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-3 text-[11px]">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <div>
                                  <p className="font-semibold text-emerald-500">
                                    Reservation Created · Ref:{" "}
                                    {String(embeddedRecord.booking_reference)}
                                  </p>
                                  <p className="text-[10px] text-[var(--muted-foreground)]">
                                    Status: {String(embeddedRecord.status)} · Total: $
                                    {String(embeddedRecord.total_amount)}{" "}
                                    {String(embeddedRecord.currency)}
                                  </p>
                                </div>
                                <Link href="/agency/bookings">
                                  <Button size="sm" variant="secondary">
                                    Open Bookings
                                    <ArrowUpRight className="h-3.5 w-3.5" />
                                  </Button>
                                </Link>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={chatBottomRef} />
              </div>

              {/* Context-Aware Suggested Replies */}
              <div className="flex flex-wrap items-center gap-1.5">
                {contextualChips.map((chip) => (
                  <button
                    key={chip.label}
                    type="button"
                    disabled={sendMessageMutation.isPending}
                    onClick={() => submitMessage(chip.prompt)}
                    className="rounded-full border border-[var(--border)] bg-[var(--background)] px-3 py-1 text-[11px] font-medium hover:border-[var(--accent)] hover:text-[var(--accent)] transition"
                  >
                    {chip.label}
                  </button>
                ))}
              </div>

              {/* Chat Input */}
              <form
                onSubmit={(e: React.FormEvent) => {
                  e.preventDefault();
                  submitMessage(draft);
                }}
                className="flex gap-2"
              >
                <Input
                  placeholder="Ask in English, বাংলা, or Banglish (e.g., 'From Dhaka on 2026-12-15', 'Berlin', 'OK')..."
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  disabled={sendMessageMutation.isPending}
                />
                <Button type="submit" disabled={sendMessageMutation.isPending || !draft.trim()}>
                  <Send className="h-4 w-4" />
                  {sendMessageMutation.isPending ? "Thinking..." : "Send"}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Side Persistent Booking State Inspector (4 cols) */}
          <Card className="lg:col-span-4 h-fit">
            <CardHeader className="border-b border-[var(--border)] pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Persistent Booking Memory</CardTitle>
                <button
                  type="button"
                  onClick={() => setShowRawJson((v) => !v)}
                  className="text-[11px] font-medium text-[var(--accent)] hover:underline"
                >
                  {showRawJson ? "Summary View" : "JSON State"}
                </button>
              </div>
              <CardDescription className="text-xs">
                Stored across turns without resetting on short replies.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4 text-xs space-y-3">
              {!lastMeta ? (
                <p className="text-[var(--muted-foreground)]">
                  Start a conversation to inspect live itinerary memory, passenger validation, and
                  booking status transitions.
                </p>
              ) : showRawJson ? (
                <pre className="max-h-96 overflow-auto rounded-lg border border-[var(--border)] bg-[var(--background)] p-2.5 text-[10px]">
                  {JSON.stringify(bookingState, null, 2)}
                </pre>
              ) : (
                <div className="space-y-2.5">
                  <div className="grid grid-cols-2 gap-2">
                    <div className="rounded-lg border border-[var(--border)] bg-[var(--background)] p-2">
                      <p className="text-[10px] text-[var(--muted-foreground)]">Origin</p>
                      <p className="font-semibold">
                        {String(bookingState.origin || "—")}
                      </p>
                    </div>
                    <div className="rounded-lg border border-[var(--border)] bg-[var(--background)] p-2">
                      <p className="text-[10px] text-[var(--muted-foreground)]">Destination</p>
                      <p className="font-semibold">
                        {String(bookingState.destination || "—")}
                      </p>
                    </div>
                    <div className="rounded-lg border border-[var(--border)] bg-[var(--background)] p-2">
                      <p className="text-[10px] text-[var(--muted-foreground)]">Departure</p>
                      <p className="font-semibold">
                        {String(bookingState.departure_date || "—")}
                      </p>
                    </div>
                    <div className="rounded-lg border border-[var(--border)] bg-[var(--background)] p-2">
                      <p className="text-[10px] text-[var(--muted-foreground)]">Cabin / Trip</p>
                      <p className="font-semibold">
                        {String(bookingState.cabin_class || "—")} ·{" "}
                        {String(bookingState.trip_type || "—")}
                      </p>
                    </div>
                  </div>

                  <div className="rounded-lg border border-[var(--border)] bg-[var(--background)] p-2.5 space-y-1">
                    <p className="text-[10px] text-[var(--muted-foreground)]">
                      Travelers &amp; Profiles
                    </p>
                    <p className="font-medium">
                      Adults: {String(bookingState.adults ?? 0)} · Children:{" "}
                      {String(bookingState.children ?? 0)} · Infants:{" "}
                      {String(bookingState.infants ?? 0)}
                    </p>
                    <p className="text-[11px] text-[var(--muted-foreground)]">
                      Stored Profiles:{" "}
                      {Array.isArray(bookingState.passengers) ? bookingState.passengers.length : 0}
                    </p>
                  </div>

                  <div className="rounded-lg border border-[var(--border)] bg-[var(--background)] p-2.5 space-y-1">
                    <p className="text-[10px] text-[var(--muted-foreground)]">Workflow Status</p>
                    <div className="flex flex-wrap gap-1.5">
                      <Badge variant="info">{currentStage}</Badge>
                      <Badge>
                        Search: {String(bookingState.flight_search_status || "NOT_STARTED")}
                      </Badge>
                    </div>
                    {typeof bookingState.booking_reference === "string" &&
                      bookingState.booking_reference && (
                        <p className="pt-1 font-semibold text-emerald-500">
                          Ref: {bookingState.booking_reference}
                        </p>
                      )}
                  </div>

                  {lastMeta.missing_slots.length > 0 && (
                    <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-2 text-[11px] text-amber-400">
                      Pending fields: {lastMeta.missing_slots.join(", ")}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      ) : (
        /* Persona & Guardrails Tab */
        <Card className="max-w-3xl">
          <CardHeader className="border-b border-[var(--border)]">
            <div className="flex items-center justify-between gap-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <Globe className="h-4 w-4 text-[var(--accent)]" />
                Consultant Persona, Languages &amp; Agency Policy
              </CardTitle>
              <Badge variant={isActive ? "success" : "warning"}>
                {isActive ? "Active" : "Paused"}
              </Badge>
            </div>
            <CardDescription>
              Shared white-label settings across your web portal, REST API, and embeddable
              widget.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-5">
            <form
              onSubmit={(e: React.FormEvent) => {
                e.preventDefault();
                saveConfigMutation.mutate();
              }}
              className="space-y-4"
            >
              <div className="flex items-center justify-between rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2.5 text-sm">
                <div>
                  <p className="font-medium">AI Auto-Response Enabled</p>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    Route incoming customer inquiries to AI before human agent escalation.
                  </p>
                </div>
                <input
                  type="checkbox"
                  aria-label="Enable AI auto-response"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="h-4 w-4 accent-[var(--accent)]"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">AI Consultant Name</label>
                <Input
                  value={agentName}
                  onChange={(e) => setAgentName(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Welcome Greeting</label>
                <textarea
                  rows={2}
                  value={welcomeMessage}
                  onChange={(e) => setWelcomeMessage(e.target.value)}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm"
                  required
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label className="text-sm font-medium">Communication Tone</label>
                  <select
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                    className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 text-sm"
                  >
                    <option value="professional">Professional Consultant</option>
                    <option value="friendly">Warm &amp; Friendly</option>
                    <option value="concise">Executive Concise</option>
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm font-medium">Auto-Handoff Turns</label>
                  <Input
                    type="number"
                    min={1}
                    max={10}
                    value={handoffThreshold}
                    onChange={(e) => setHandoffThreshold(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Supported Languages</label>
                <div className="flex flex-wrap gap-2">
                  {LANGUAGE_OPTIONS.map((langOpt) => {
                    const selected = supportedLanguages.includes(langOpt.code);
                    return (
                      <button
                        key={langOpt.code}
                        type="button"
                        onClick={() => toggleLanguage(langOpt.code)}
                        className={`rounded-md border px-3 py-1.5 text-xs font-medium transition ${
                          selected
                            ? "border-[var(--accent)] bg-[var(--accent)]/15 text-[var(--accent)]"
                            : "border-[var(--border)] bg-[var(--background)] text-[var(--muted-foreground)]"
                        }`}
                      >
                        {langOpt.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">
                  Agency Policy &amp; Custom Instructions
                </label>
                <textarea
                  rows={3}
                  value={customInstructions}
                  onChange={(e) => setCustomInstructions(e.target.value)}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-xs"
                  placeholder="e.g., Always highlight refundable fare options, baggage limits, and offer human support for multi-city group inquiries."
                />
              </div>

              <Button type="submit" disabled={saveConfigMutation.isPending}>
                <CheckCircle2 className="h-4 w-4" />
                {saveConfigMutation.isPending ? "Saving..." : "Save Consultant Setup"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}
    </DashboardShell>
  );
}

export default function AgencyAgentsPage() {
  return (
    <RoleGuard allowedRoles={["AGENCY_OWNER", "AGENCY_MANAGER"]}>
      <AgencyAgentsContent />
    </RoleGuard>
  );
}
