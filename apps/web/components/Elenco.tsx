"use client";
import { useState } from "react";
import type { SoggettoPagina } from "@/lib/contenuti";
import { SchedaBreve } from "./Soggetto";

export function Elenco({ partiti, persone }: { partiti: SoggettoPagina[]; persone: SoggettoPagina[] }) {
  const [vista, setVista] = useState<"partiti" | "persone">("partiti");
  const lista = vista === "partiti" ? partiti : persone;
  return (
    <>
      <div className="tabs" role="group" aria-label="Partiti o persone">
        <button type="button" aria-pressed={vista === "partiti"} onClick={() => setVista("partiti")}>
          Partiti
        </button>
        <button type="button" aria-pressed={vista === "persone"} onClick={() => setVista("persone")}>
          Persone
        </button>
      </div>
      {lista.map((s) => (
        <SchedaBreve key={s.slug} s={s} />
      ))}
    </>
  );
}
