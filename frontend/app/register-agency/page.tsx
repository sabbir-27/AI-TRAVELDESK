import { SiteHeader } from "@/components/site-header";
import { AgencyRegisterForm } from "@/features/saas/agency-register-form";

export default function RegisterAgencyPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <SiteHeader />
      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <AgencyRegisterForm />
      </main>
    </div>
  );
}
