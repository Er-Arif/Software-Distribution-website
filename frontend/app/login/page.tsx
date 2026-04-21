import { Shell } from "@/components/ui";

export default function LoginPage() {
  return (
    <Shell>
      <section className="mx-auto max-w-md px-6 py-12">
        <h1 className="text-3xl font-bold">Login</h1>
        <form className="mt-6 space-y-4 rounded-md border border-slate-200 bg-white p-5">
          <input className="w-full rounded-md border border-slate-300 px-3 py-2" placeholder="Email" type="email" />
          <input className="w-full rounded-md border border-slate-300 px-3 py-2" placeholder="Password" type="password" />
          <button className="w-full rounded-md bg-brand px-4 py-2 font-semibold text-white">Sign in</button>
        </form>
      </section>
    </Shell>
  );
}
