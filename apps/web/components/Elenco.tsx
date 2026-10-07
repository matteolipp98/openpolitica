"use client";
import Link from "next/link";
import { useState } from "react";
import { Accostamento } from "./Accostamento";
import { Righe, type Riga } from "./Righe";
import type { Accostamento as A } from "@/lib/tipi";

export interface Scheda { slug: string; tipo: "partito" | "persona"; nome: string; ruolo: string; frase: string; righe: Riga[]; esempio?: A }

export function Elenco({ partiti, persone }: { partiti: Scheda[]; persone: Scheda[] }) {
  const [vista, setVista] = useState<"partiti" | "persone">("partiti");
  const lista = vista === "partiti" ? partiti : persone;
  return (
    <>
      <div className="tabs" role="group" aria-label="Partiti o persone">
        <button type="button" aria-pressed={vista === "partiti"} onClick={() => setVista("partiti")}>Partiti</button>
        <button type="button" aria-pressed={vista === "persone"} onClick={() => setVista("persone")}>Persone</button>
      </div>
      {lista.map((s) => (
        <details className="card" key={s.slug}>
          <summary>
            <span className="nome">{s.nome}</span>
            <div className="ruolo">{s.ruolo}</div>
            <p className="frase">{s.frase}</p>
            <span className="apri">
              <span className="chiuso">Vedi i dettagli ▾</span>
              <span className="aperto">Chiudi ▴</span>
            </span>
          </summary>
          <Righe righe={s.righe} />
          {s.esempio && <div style={{ margin: "0 18px" }}><Accostamento a={s.esempio} /></div>}
          <p className="piccolo">
            <Link href={`/${s.tipo === "partito" ? "partiti" : "persone"}/${s.slug}`}>Apri la scheda</Link>. Qui non diciamo
            se le sue idee sono buone: quello lo decidi tu.
          </p>
        </details>
      ))}
    </>
  );
}
