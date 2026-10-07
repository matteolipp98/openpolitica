import Link from "next/link";
import { GraficoTempo } from "./GraficoTempo";
import { NotaEsempio } from "./NotaEsempio";
import { metricheTempo, nomeTrimestre, schedeTempo, trimestri } from "@/lib/andamento";
import { pacchetto, parametri } from "@/lib/dati";
import type { MetricaTempo } from "@/lib/tipi";

/** "Com'è cambiato nel tempo" (ADR 0040), una metrica per volta. */
export function PaginaTempo({ metrica }: { metrica: MetricaTempo }) {
  const tutte = metricheTempo();
  const m = tutte.find((x) => x.id === metrica)!;
  const etichette = trimestri().map(nomeTrimestre);
  const minimo = parametri().presentazione.denominatoreMinimo;
  const esempio = pacchetto().manifest.esempio;

  return (
    <main>
      <h1>Com&apos;è cambiato nel tempo</h1>
      <p className="lede">Scegli cosa guardare. Ogni punto sono tre mesi. Confrontiamo l&apos;ultimo anno con quello prima.</p>
      <NotaEsempio />

      <h2>Cosa vuoi guardare?</h2>
      <div className="scelte">
        {tutte.map((x) => (
          <Link key={x.id} href={x.id === "vota_con_governo" ? "/nel-tempo" : `/nel-tempo/${x.id}`}
            aria-current={x.id === metrica ? "page" : undefined}>
            {x.nome}{x.presto && <span className="presto"> · in arrivo</span>}
          </Link>
        ))}
      </div>
      <p className="spiega">
        {m.spiega}
        {m.presto && (esempio
          ? <> <b>Per ora è un esempio:</b> arriva quando leggeremo anche cosa dicono i partiti.</>
          : <> Arriva quando leggeremo anche cosa dicono i partiti.</>)}
      </p>
      <div className="legenda">
        <span><i />Al governo</span>
        <span><i className="p" />Tre mesi</span>
        <span>Punto mancante: in quei tre mesi abbiamo troppo pochi dati</span>
      </div>

      {schedeTempo(m).map((s) => (
        <section className="card tempo" key={s.id}>
          <p className="nome"><Link href={`/partiti/${s.id}`}>{s.nome}</Link></p>
          <p className="ruolo">{s.ruolo}{s.nota && ` · ${s.nota}`}</p>
          <div className="testa">
            <span className="cifra">{s.cifra}</span>
            <p className="frase">
              {s.frase} <span className="verdetto">{s.verdetto}</span>
              <span className="sotto">{s.prima}</span>
            </p>
          </div>
          <GraficoTempo punti={s.punti} etichette={etichette} minimo={minimo} titolo={`${s.nome}, ${m.nome}`} />
        </section>
      ))}

      <p className="chiusura">
        Non diciamo se un cambiamento è un bene o un male. Votare uniti, o insieme al governo, può essere un pregio o un difetto: lo decidi tu.
      </p>
    </main>
  );
}
