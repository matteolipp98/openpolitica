import Link from "next/link";
import { notFound } from "next/navigation";
import { InCostruzione } from "@/components/InCostruzione";
import { RigheVuote } from "@/components/Soggetto";
import { persone } from "@/lib/contenuti";

export const dynamicParams = false;
export function generateStaticParams() {
  return persone().map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return { title: persone().find((p) => p.slug === slug)?.nome };
}

export default async function SchedaPersona({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const p = persone().find((x) => x.slug === slug);
  if (!p) notFound();
  return (
    <main>
      <Link className="back" href="/">← Tutte le persone</Link>
      <h1>{p.nome}</h1>
      <p className="ruolo">{p.ruolo}</p>
      <InCostruzione />
      <div className="card" style={{ marginTop: 22 }}>
        <RigheVuote />
      </div>
      <p className="chiusura">
        Qui non diciamo se le sue idee sono buone o cattive. Diciamo cosa ha detto e cosa ha fatto. Il resto lo decidi
        tu.
      </p>
    </main>
  );
}
