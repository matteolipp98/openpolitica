import Link from "next/link";
import { Elenco, type Scheda } from "@/components/Elenco";
import { NotaEsempio } from "@/components/NotaEsempio";
import { righe } from "@/lib/righe";
import { pacchetto, partiti, persone, parametri } from "@/lib/dati";
import { fraseNumeri, letture } from "@/lib/letture";
import type { Soggetto } from "@/lib/tipi";

function scheda(s: Soggetto): Scheda {
  return {
    slug: s.slug, tipo: s.tipo, nome: s.nome, ruolo: s.ruolo,
    frase: fraseNumeri(s) ?? fraseVoti(s) ?? "Per ora non abbiamo ancora dati da mostrare.",
    righe: righe(s),
    esempio: pacchetto().accostamenti[s.id]?.[0],
  };
}

/** Senza dati controllati, per i partiti si dice almeno come votano: stessa metrica per tutti (ADR 0040). */
function fraseVoti(s: Soggetto): string | null {
  const serie = pacchetto().andamento.serie[s.id]?.vota_compatto;
  if (!serie) return null;
  const n = serie.reduce((a, p) => a + p.n, 0), d = serie.reduce((a, p) => a + p.d, 0);
  return d ? `Nei voti finali in Parlamento, il partito ha votato unito ${n} volte su ${d}.` : null;
}

/** Mette in grassetto i nomi dentro una frase generata. */
function conNomi(testo: string, nomi: string[]) {
  if (!nomi.length) return testo;
  const parti = testo.split(new RegExp(`(${nomi.map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`));
  return parti.map((p, i) => (nomi.includes(p) ? <b key={i}>{p}</b> : p));
}

export default function Indice() {
  const { sezioni } = pacchetto().manifest;
  const inBreve = sezioni.letture ? letture(partiti()) : [];
  return (
    <main>
      <h1>Cosa hanno fatto davvero</h1>
      <p className="lede">Quando un politico dice un dato, per esempio quanti posti di lavoro ci sono, controlliamo se è vero. E guardiamo come vota in Parlamento.</p>
      <NotaEsempio />
      {inBreve.length > 0 && (
        <>
          <h2>In breve</h2>
          <div className="card letture">
            {inBreve.map((l) => (
              <div className="riga" key={l.testo}>
                <span className={`cifra${l.cifra.endsWith("%") || !l.nomi.length ? " b" : ""}`}>{l.cifra}</span>
                <div className="testo">
                  <p>{conNomi(l.testo, l.nomi)}</p>
                  <p className="sotto">{l.sotto}</p>
                </div>
              </div>
            ))}
          </div>
          <p className="piccolo" style={{ margin: "10px 0 0" }}>
            Confrontiamo solo chi ha detto almeno {parametri().presentazione.denominatoreMinimo} dati: con meno, il confronto non sarebbe giusto.
          </p>
        </>
      )}
      <h2>Tutti</h2>
      <Elenco partiti={partiti().map(scheda)} persone={persone().map(scheda)} />
    </main>
  );
}
