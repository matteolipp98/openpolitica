import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { PaginaTempo } from "@/components/PaginaTempo";
import { metricheTempo } from "@/lib/andamento";
import type { MetricaTempo } from "@/lib/tipi";

export const dynamicParams = false;

export function generateStaticParams() {
  return metricheTempo().filter((m) => m.id !== "vota_con_governo").map((m) => ({ metrica: m.id }));
}

export async function generateMetadata({ params }: { params: Promise<{ metrica: string }> }): Promise<Metadata> {
  const { metrica } = await params;
  const m = metricheTempo().find((x) => x.id === metrica);
  return { title: m ? `${m.nome} nel tempo` : "Nel tempo" };
}

export default async function NelTempoMetrica({ params }: { params: Promise<{ metrica: string }> }) {
  const { metrica } = await params;
  if (!metricheTempo().some((m) => m.id === metrica)) notFound();
  return <PaginaTempo metrica={metrica as MetricaTempo} />;
}
