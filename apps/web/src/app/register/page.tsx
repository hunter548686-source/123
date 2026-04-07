import { AuthPanel } from "@/components/auth-panel";

export default function RegisterPage() {
  return (
    <main className="min-h-screen px-5 py-8 sm:px-8 lg:px-12">
      <AuthPanel defaultMode="register" />
    </main>
  );
}
