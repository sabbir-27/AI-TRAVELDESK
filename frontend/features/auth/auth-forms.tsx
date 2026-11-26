"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { getHomeRouteForRole } from "@/components/role-guard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api-client";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginValues = z.infer<typeof loginSchema>;

const registerSchema = z.object({
  full_name: z.string().min(2, "Full name must be at least 2 characters").max(200),
  email: z.string().email("Enter a valid email address"),
  phone: z.string().max(40).optional(),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .max(128, "Password is too long"),
});

type RegisterValues = z.infer<typeof registerSchema>;

export function LoginForm() {
  const router = useRouter();
  const { login } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (values: LoginValues) => {
    setServerError(null);
    try {
      const profile = await login(values);
      router.push(getHomeRouteForRole(profile.role));
    } catch (err) {
      setServerError(
        err instanceof ApiError ? err.detail : "Unable to sign in. Please try again."
      );
    }
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Sign in to AI TravelDesk</CardTitle>
        <CardDescription>Access your workspace with your account credentials.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          {serverError && (
            <div
              role="alert"
              className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400"
            >
              {serverError}
            </div>
          )}

          <div className="space-y-1.5">
            <label htmlFor="login-email" className="text-sm font-medium">
              Email
            </label>
            <Input
              id="login-email"
              type="email"
              autoComplete="email"
              placeholder="agent@agency.com"
              {...register("email")}
            />
            {errors.email && (
              <p className="text-xs text-red-600 dark:text-red-400">{errors.email.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <label htmlFor="login-password" className="text-sm font-medium">
              Password
            </label>
            <Input
              id="login-password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              {...register("password")}
            />
            {errors.password && (
              <p className="text-xs text-red-600 dark:text-red-400">{errors.password.message}</p>
            )}
          </div>

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Signing in..." : "Sign in"}
          </Button>

          <p className="text-center text-sm text-[var(--muted-foreground)]">
            Need an account?{" "}
            <Link href="/register" className="font-medium text-[var(--accent)] hover:underline">
              Create one
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}

export function RegisterForm() {
  const router = useRouter();
  const { register: registerUser } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (values: RegisterValues) => {
    setServerError(null);
    try {
      await registerUser({
        email: values.email,
        password: values.password,
        full_name: values.full_name,
        phone: values.phone || undefined,
      });
      router.push("/dashboard");
    } catch (err) {
      setServerError(
        err instanceof ApiError ? err.detail : "Unable to register. Please try again."
      );
    }
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Create your account</CardTitle>
        <CardDescription>Register for AI TravelDesk platform access.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          {serverError && (
            <div
              role="alert"
              className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400"
            >
              {serverError}
            </div>
          )}

          <div className="space-y-1.5">
            <label htmlFor="register-name" className="text-sm font-medium">
              Full name
            </label>
            <Input
              id="register-name"
              type="text"
              autoComplete="name"
              placeholder="Amina Rahman"
              {...register("full_name")}
            />
            {errors.full_name && (
              <p className="text-xs text-red-600 dark:text-red-400">{errors.full_name.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <label htmlFor="register-email" className="text-sm font-medium">
              Work or personal email
            </label>
            <Input
              id="register-email"
              type="email"
              autoComplete="email"
              placeholder="amina@example.com"
              {...register("email")}
            />
            {errors.email && (
              <p className="text-xs text-red-600 dark:text-red-400">{errors.email.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <label htmlFor="register-phone" className="text-sm font-medium">
              Phone (optional)
            </label>
            <Input
              id="register-phone"
              type="tel"
              autoComplete="tel"
              placeholder="+8801700000000"
              {...register("phone")}
            />
            {errors.phone && (
              <p className="text-xs text-red-600 dark:text-red-400">{errors.phone.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <label htmlFor="register-password" className="text-sm font-medium">
              Password
            </label>
            <Input
              id="register-password"
              type="password"
              autoComplete="new-password"
              placeholder="Minimum 8 characters"
              {...register("password")}
            />
            {errors.password && (
              <p className="text-xs text-red-600 dark:text-red-400">{errors.password.message}</p>
            )}
          </div>

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Creating account..." : "Create account"}
          </Button>

          <p className="text-center text-sm text-[var(--muted-foreground)]">
            Already registered?{" "}
            <Link href="/login" className="font-medium text-[var(--accent)] hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
