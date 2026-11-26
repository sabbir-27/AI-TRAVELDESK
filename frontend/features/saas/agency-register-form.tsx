"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api-client";
import { saasService } from "@/services/saas-service";

const agencyRegisterSchema = z.object({
  agency_name: z.string().min(2, "Agency name must be at least 2 characters").max(200),
  slug: z
    .string()
    .regex(/^[a-z0-9-]+$/, "Slug must use lowercase letters, numbers, or hyphens")
    .optional()
    .or(z.literal("")),
  contact_email: z.string().email("Enter a valid agency contact email"),
  country_code: z.string().length(2, "Use a 2-letter country code (e.g. BD, US)"),
  default_currency: z.string().length(3, "Use a 3-letter currency code (e.g. USD, BDT)"),
  plan_tier: z.enum(["STARTER", "PROFESSIONAL", "BUSINESS", "ENTERPRISE"]),
  billing_cycle: z.enum(["MONTHLY", "ANNUAL"]),
  owner_full_name: z.string().min(2, "Owner full name is required").max(200),
  owner_email: z.string().email("Enter a valid owner email"),
  owner_password: z.string().min(8, "Password must be at least 8 characters").max(128),
});

type AgencyRegisterValues = z.infer<typeof agencyRegisterSchema>;

export function AgencyRegisterForm() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AgencyRegisterValues>({
    resolver: zodResolver(agencyRegisterSchema),
    defaultValues: {
      country_code: "BD",
      default_currency: "USD",
      plan_tier: "STARTER",
      billing_cycle: "MONTHLY",
    },
  });

  const onSubmit = async (values: AgencyRegisterValues) => {
    setServerError(null);
    try {
      await saasService.registerAgency({
        ...values,
        slug: values.slug || undefined,
      });
      await refreshUser();
      router.push("/agency/dashboard");
    } catch (err) {
      setServerError(
        err instanceof ApiError ? err.detail : "Unable to register agency. Please try again."
      );
    }
  };

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <CardTitle>Onboard Your Travel Agency</CardTitle>
        <CardDescription>
          Register an isolated multi-tenant workspace. Super Admin approval activates live API &
          booking operations.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
          {serverError && (
            <div
              role="alert"
              className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400"
            >
              {serverError}
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <label htmlFor="agency-name" className="text-sm font-medium">
                Agency Name
              </label>
              <Input
                id="agency-name"
                placeholder="Dhaka Sky Travels"
                {...register("agency_name")}
              />
              {errors.agency_name && (
                <p className="text-xs text-red-600 dark:text-red-400">
                  {errors.agency_name.message}
                </p>
              )}
            </div>

            <div className="space-y-1.5">
              <label htmlFor="agency-slug" className="text-sm font-medium">
                Workspace Slug (optional)
              </label>
              <Input id="agency-slug" placeholder="dhaka-sky" {...register("slug")} />
              {errors.slug && (
                <p className="text-xs text-red-600 dark:text-red-400">{errors.slug.message}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <label htmlFor="agency-contact-email" className="text-sm font-medium">
                Agency Contact Email
              </label>
              <Input
                id="agency-contact-email"
                type="email"
                placeholder="ops@dhakasky.com"
                {...register("contact_email")}
              />
              {errors.contact_email && (
                <p className="text-xs text-red-600 dark:text-red-400">
                  {errors.contact_email.message}
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label htmlFor="agency-country" className="text-sm font-medium">
                  Country
                </label>
                <Input id="agency-country" maxLength={2} {...register("country_code")} />
                {errors.country_code && (
                  <p className="text-xs text-red-600 dark:text-red-400">
                    {errors.country_code.message}
                  </p>
                )}
              </div>
              <div className="space-y-1.5">
                <label htmlFor="agency-currency" className="text-sm font-medium">
                  Currency
                </label>
                <Input id="agency-currency" maxLength={3} {...register("default_currency")} />
                {errors.default_currency && (
                  <p className="text-xs text-red-600 dark:text-red-400">
                    {errors.default_currency.message}
                  </p>
                )}
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="plan-tier" className="text-sm font-medium">
                SaaS Plan
              </label>
              <select
                id="plan-tier"
                className="flex h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm"
                {...register("plan_tier")}
              >
                <option value="STARTER">Starter ($49/mo)</option>
                <option value="PROFESSIONAL">Professional ($149/mo)</option>
                <option value="BUSINESS">Business ($399/mo)</option>
                <option value="ENTERPRISE">Enterprise ($999/mo)</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="billing-cycle" className="text-sm font-medium">
                Billing Cycle
              </label>
              <select
                id="billing-cycle"
                className="flex h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm"
                {...register("billing_cycle")}
              >
                <option value="MONTHLY">Monthly</option>
                <option value="ANNUAL">Annual</option>
              </select>
            </div>
          </div>

          <hr className="border-[var(--border)]" />

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <label htmlFor="owner-name" className="text-sm font-medium">
                Owner Full Name
              </label>
              <Input
                id="owner-name"
                placeholder="Tariq Hasan"
                {...register("owner_full_name")}
              />
              {errors.owner_full_name && (
                <p className="text-xs text-red-600 dark:text-red-400">
                  {errors.owner_full_name.message}
                </p>
              )}
            </div>

            <div className="space-y-1.5">
              <label htmlFor="owner-email" className="text-sm font-medium">
                Owner Login Email
              </label>
              <Input
                id="owner-email"
                type="email"
                placeholder="tariq@dhakasky.com"
                {...register("owner_email")}
              />
              {errors.owner_email && (
                <p className="text-xs text-red-600 dark:text-red-400">
                  {errors.owner_email.message}
                </p>
              )}
            </div>

            <div className="space-y-1.5 sm:col-span-2">
              <label htmlFor="owner-password" className="text-sm font-medium">
                Owner Password
              </label>
              <Input
                id="owner-password"
                type="password"
                placeholder="Minimum 8 characters"
                {...register("owner_password")}
              />
              {errors.owner_password && (
                <p className="text-xs text-red-600 dark:text-red-400">
                  {errors.owner_password.message}
                </p>
              )}
            </div>
          </div>

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Creating agency workspace..." : "Register Agency"}
          </Button>

          <p className="text-center text-sm text-[var(--muted-foreground)]">
            Already onboarded?{" "}
            <Link href="/login" className="font-medium text-[var(--accent)] hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
