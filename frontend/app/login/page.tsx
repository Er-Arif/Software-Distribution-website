import { Shell } from "@/components/ui";
import { LoginForm } from "@/components/auth-forms";

export default function LoginPage() {
  return (
    <Shell>
      <section className="mx-auto max-w-md px-6 py-12">
        <h1 className="text-3xl font-bold">Login</h1>
        <LoginForm />
      </section>
    </Shell>
  );
}
