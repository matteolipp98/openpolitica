import { notFound } from "next/navigation";
import { SchedaSoggetto } from "@/components/SchedaSoggetto";
import { persone } from "@/lib/dati";

export const dynamicParams = false;
export function generateStaticParams() {
  return persone().map((s) => ({ slug: s.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return { title: persone().find((s) => s.slug === slug)?.nome };
}

export default async function Pagina({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const s = persone().find((x) => x.slug === slug);
  if (!s) notFound();
  return <SchedaSoggetto s={s} />;
}
