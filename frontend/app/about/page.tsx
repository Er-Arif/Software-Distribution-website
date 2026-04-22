import { Shell } from "@/components/ui";

export default function AboutPage() {
  return (
    <Shell>
      <section className="mx-auto max-w-4xl px-6 py-12">
        <h1 className="text-3xl font-bold">About</h1>
        <p className="mt-3 text-slate-600">
          This platform powers secure discovery, purchase, licensing, downloads, and updates for desktop software.
        </p>
      </section>
    </Shell>
  );
}
