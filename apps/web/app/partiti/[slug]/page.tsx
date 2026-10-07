import Link from "next/link";
import { notFound } from "next/navigation";
import { InCostruzione } from "@/components/InCostruzione";
import { RigheVuote } from "@/components/Soggetto";
import { partiti } from "@/lib/contenuti";

export const dynamicParams = false;
export function generateStaticParams() {
  return partiti().map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return { title: partiti().find((p) => p.slug === slug)?.nome };
}

export default async function SchedaPartito({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const p = partiti().find((x) => x.slug === slug);
  if (!p) notFound();
  return (
    <main>
      <Link className="back" href="/">← Tutti i partiti</Link>
      <h1>{p.nome}</h1>
      <p className="ruolo">{p.ruolo}</p>
      <InCostruzione />
      <div className="card" style={{ marginTop: 22 }}>
        <RigheVuote />
      </div>
      <p className="chiusura">
        Qui non diciamo se le loro idee sono buone o cattive. Diciamo cosa hanno detto e cosa hanno fatto. Il resto lo
        decidi tu.
      </p>
    </main>
  );
}
