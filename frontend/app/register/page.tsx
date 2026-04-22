import { Shell } from "@/components/ui";

export default function RegisterPage() {
  return (
    <Shell>
      <section className="mx-auto max-w-md px-6 py-12">
        <h1 className="text-3xl font-bold">Register</h1>
        <p className="mt-3 text-slate-600">
          Customer registration is available through the API and can be expanded into a full form when public signups are enabled.
        </p>
      </section>
    </Shell>
  );
}
