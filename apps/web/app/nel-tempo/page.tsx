import type { Metadata } from "next";
import { PaginaTempo } from "@/components/PaginaTempo";

export const metadata: Metadata = { title: "Com'è cambiato nel tempo" };

export default function NelTempo() {
  return <PaginaTempo metrica="vota_con_governo" />;
}
