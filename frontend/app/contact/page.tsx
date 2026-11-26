"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { PublicShell } from "@/components/layout/public-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";

const contactSchema = z.object({
  name: z.string().min(2, "Name is required"),
  email: z.string().email("Enter a valid email address"),
  agency: z.string().min(2, "Agency or company name is required"),
  message: z.string().min(10, "Please share at least 10 characters about your inquiry"),
});

type ContactValues = z.infer<typeof contactSchema>;

export default function ContactPage() {
  const { pushToast } = useToast();
  const [submitted, setSubmitted] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ContactValues>({
    resolver: zodResolver(contactSchema),
  });

  const onSubmit = () => {
    setSubmitted(true);
    pushToast({
      variant: "success",
      title: "Inquiry recorded",
      description: "Our enterprise onboarding team will follow up via email.",
    });
    reset();
  };

  return (
    <PublicShell>
      <section className="mx-auto max-w-2xl space-y-6 px-4 py-16 sm:px-6">
        <Badge variant="info">Contact Sales &amp; Support</Badge>
        <Card>
          <CardHeader>
            <CardTitle>Get in touch with AI TravelDesk</CardTitle>
            <CardDescription>
              Ask about Enterprise GDS integration, custom SLA plans, or agency onboarding.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {submitted && (
              <div className="mb-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-600 dark:text-emerald-400">
                Thank you — your message has been captured for follow-up.
              </div>
            )}
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <div className="space-y-1.5">
                <label htmlFor="contact-name" className="text-sm font-medium">
                  Your Name
                </label>
                <Input id="contact-name" placeholder="Tariq Hasan" {...register("name")} />
                {errors.name && (
                  <p className="text-xs text-red-600 dark:text-red-400">{errors.name.message}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <label htmlFor="contact-email" className="text-sm font-medium">
                  Work Email
                </label>
                <Input
                  id="contact-email"
                  type="email"
                  placeholder="tariq@agency.com"
                  {...register("email")}
                />
                {errors.email && (
                  <p className="text-xs text-red-600 dark:text-red-400">{errors.email.message}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <label htmlFor="contact-agency" className="text-sm font-medium">
                  Agency / Company
                </label>
                <Input
                  id="contact-agency"
                  placeholder="Dhaka Sky Travels"
                  {...register("agency")}
                />
                {errors.agency && (
                  <p className="text-xs text-red-600 dark:text-red-400">{errors.agency.message}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <label htmlFor="contact-message" className="text-sm font-medium">
                  Message
                </label>
                <textarea
                  id="contact-message"
                  rows={4}
                  placeholder="Tell us about your monthly booking volume and GDS requirements..."
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                  {...register("message")}
                />
                {errors.message && (
                  <p className="text-xs text-red-600 dark:text-red-400">{errors.message.message}</p>
                )}
              </div>

              <Button type="submit" className="w-full">
                Send Message
              </Button>
            </form>
          </CardContent>
        </Card>
      </section>
    </PublicShell>
  );
}
