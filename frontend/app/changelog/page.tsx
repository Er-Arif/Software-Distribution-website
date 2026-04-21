import { Shell } from "@/components/ui";

export default function ChangelogPage() {
  return (
    <Shell>
      <section className="mx-auto max-w-4xl px-6 py-12">
        <h1 className="text-3xl font-bold">Release Notes</h1>
        <p className="mt-3 text-slate-600">Published changelogs can be public or restricted by plan entitlement.</p>
      </section>
    </Shell>
  );
}
