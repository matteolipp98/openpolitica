import type { Metadata } from "next";
import Link from "next/link";
import { NotaEsempio } from "@/components/NotaEsempio";
import { Questionario } from "@/components/Questionario";
import { pacchetto, parametri, partiti } from "@/lib/dati";

export const metadata: Metadata = { title: "Chi la pensa come te" };

export default function Domande() {
  const { domande, posizioni, manifest } = pacchetto();
  const soggetti = partiti().map((p) => ({
    id: p.id,
    nome: p.nome,
    ruolo: p.ruolo,
    tipo: "partito" as const,
    posizioni: Object.fromEntries(
      Object.entries(posizioni[p.id] ?? {}).map(([k, v]) => [k, { valore: v.valore, stato: v.stato, confidenza: v.valore === null ? null : ("piena" as const) }]),
    ),
  }));
  return (
    <main>
      <h1>Chi la pensa come te</h1>
      <NotaEsempio />
      {manifest.catalogo.stato === "provvisorio" && !manifest.esempio && domande.length > 0 && (
        <p className="nota">Le domande sono state scritte e controllate da un sistema di intelligenza artificiale. Le stiamo ancora verificando.</p>
      )}
      {domande.length > 0 ? (
        <Questionario domande={domande} soggetti={soggetti} parametri={parametri().affinita} catalogo={manifest.catalogo.versione} />
      ) : (
        <p className="vuota">
          Le domande arrivano presto. Le ricaviamo dai voti in Parlamento su cui i partiti si sono divisi di più, e stiamo
          finendo di caricarli.
        </p>
      )}
      <p className="chiusura">
        Le posizioni dei partiti vengono dai voti in Parlamento. Le tue risposte restano sul tuo telefono o sul tuo computer.{" "}
        <Link href="/come-funziona">Come funziona</Link>
      </p>
    </main>
  );
}
