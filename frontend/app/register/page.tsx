import { SiteHeader } from "@/components/site-header";
import { RegisterForm } from "@/features/auth/auth-forms";

export default function RegisterPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <SiteHeader />
      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <RegisterForm />
      </main>
    </div>
  );
}
