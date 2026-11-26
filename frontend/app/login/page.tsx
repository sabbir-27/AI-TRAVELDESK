import { SiteHeader } from "@/components/site-header";
import { LoginForm } from "@/features/auth/auth-forms";

export default function LoginPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <SiteHeader />
      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <LoginForm />
      </main>
    </div>
  );
}
