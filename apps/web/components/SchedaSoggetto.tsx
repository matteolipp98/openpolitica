import Link from "next/link";
import { Accostamento } from "./Accostamento";
import { NotaEsempio } from "./NotaEsempio";
import { pacchetto } from "@/lib/dati";
import { quota } from "@/lib/letture";
import type { Posizione, Soggetto } from "@/lib/tipi";

const ETICHETTA: Record<string, [string, string]> = {
  si: ["A favore", "si"],
  no: ["Contro", "no"],
  zero: ["Né sì né no", "vuoto"],
  vuoto: ["Non si sa", "vuoto"],
};

function etichetta(p?: Posizione): [string, string] {
  if (!p || p.valore === null) return ETICHETTA.vuoto!;
  return p.valore > 0 ? ETICHETTA.si! : p.valore < 0 ? ETICHETTA.no! : ETICHETTA.zero!;
}

const STATO = { mantenuta: "Mantenuta", a_meta: "A metà", non_mantenuta: "Non mantenuta" } as const;

export function SchedaSoggetto({ s }: { s: Soggetto }) {
  const { domande, posizioni, promesse, accostamenti } = pacchetto();
  const pos = posizioni[s.id] ?? {};
  const prom = promesse[s.id] ?? [];
  const numeri = (accostamenti[s.id] ?? []).filter((a) => a.esito);
  const delPartito = s.partito ? pacchetto().soggetti.find((x) => x.id === s.partito) : s;
  const governo = /governo/i.test(delPartito?.ruolo ?? "");
  const chi = s.tipo === "partito" ? "loro" : "sue";

  const sommario = [
    s.numeri && `Ha detto un dato sbagliato ${s.numeri.sbagliati} volte su ${s.numeri.controllati} che abbiamo controllato.`,
    s.coerenza && `Ha detto una cosa e ha votato il contrario ${s.coerenza.contrari} volte su ${s.coerenza.confrontabili}.`,
    s.promesse && `Ha mantenuto ${s.promesse.mantenute} promesse su ${s.promesse.totali}.`,
  ].filter(Boolean) as string[];

  return (
    <main>
      <Link className="back" href="/">← Tutti {s.tipo === "partito" ? "i partiti" : "i politici"}</Link>
      <h1>{s.nome}</h1>
      <p className="ruolo">{s.ruolo}</p>
      {sommario.length > 0 && (
        <div className="sommario">{sommario.map((f) => <p key={f}>{f}</p>)}</div>
      )}
      <NotaEsempio />

      <h2>Come ha votato sulle cose che contano</h2>
      {domande.length === 0 && (
        <p className="vuota">Arriva presto. Stiamo scegliendo i voti in Parlamento su cui i partiti si sono divisi di più.</p>
      )}
      {domande.map((d) => {
        const p = pos[d.id];
        const [et, cls] = etichetta(p);
        return (
          <details className="tema" key={d.id}>
            <summary>
              <span className={`pos ${cls}`}>{et}</span>
              <span className="q">{d.testo}</span>
              <span className="apri"><span className="chiuso">vedi ▾</span><span className="aperto">chiudi ▴</span></span>
            </summary>
            <div className="dett">
              {p && p.evidenze.length > 0 ? (
                p.evidenze.map((e) => (
                  <div className="voto" key={e.testo + e.quando}><b>{e.testo}</b><span>{e.quando}</span></div>
                ))
              ) : (
                <div className="voto"><b>In Parlamento non si è mai votato su questo.</b><span>Non inventiamo la {chi} posizione.</span></div>
              )}
              {p?.nota && (
                <div className="conf"><div><p className="et">Attenzione</p><p>{p.nota}</p></div></div>
              )}
            </div>
          </details>
        );
      })}

      <h2>Le promesse del programma</h2>
      <p className="ruolonota">
        {governo
          ? "Era al governo, quindi poteva fare le leggi. Chi sta all'opposizione ne mantiene meno per forza."
          : "Era all'opposizione: non poteva fare le leggi da solo, quindi ne mantiene meno per forza."}
      </p>
      {prom.length > 0 ? (
        <div className="prom">
          {prom.map((p) => (
            <div className="pr" key={p.testo}>
              <span className={`tag ${p.stato}`}>{STATO[p.stato]}</span>
              <p>{p.testo}<span>{p.motivo}</span></p>
            </div>
          ))}
        </div>
      ) : (
        <p className="vuota">Non abbiamo ancora letto il programma una promessa per volta. Lo faremo, e qui vedrai quali ha mantenuto.</p>
      )}

      <h2>Come sono fatte le {chi} promesse</h2>
      <p className="ruolonota">
        Contiamo le promesse e gli annunci fatti in Parlamento, sui canali ufficiali e nelle interviste. Non diciamo se sono buone idee.
      </p>
      <div className="card">
        {(s.indicatori
          ? [
              ["Promesse precise", s.indicatori.precise, "Dicono quanto e entro quando, per esempio «20.000 insegnanti entro il 2027».", false],
              ["Promesse che dicono dove prendere i soldi", s.indicatori.soldi, "Su quelle che costano soldi pubblici.", true],
              ["Annunci fatti in tempo", s.indicatori.inTempo, "Aveva detto «entro giugno» ed entro giugno c'era una legge o una proposta.", false],
              ["Frasi per attaccare gli altri partiti", s.indicatori.attacchi, "Le altre parlano di cosa vuole fare o di cosa ha fatto.", true],
            ].map(([t, c, spiega, b]) => {
              const q = quota((c as { n: number }).n, (c as { d: number }).d);
              return (
                <div className="riga" key={t as string}>
                  <span className={`cifra${b ? " b" : ""}`}>{q.cifra}</span>
                  <div className="testo"><p>{t as string}</p><p className="sotto">{spiega as string} {q.sotto}.{q.pochi}</p></div>
                </div>
              );
            })
          : (
            <div className="riga">
              <span className="cifra vuota">—</span>
              <div className="testo">
                <p>Promesse precise, promesse che dicono dove prendere i soldi, annunci fatti in tempo</p>
                <p className="sotto">Arriva quando leggeremo ogni giorno cosa dicono i partiti.</p>
              </div>
            </div>
          ))}
      </div>

      <h2>Dati sbagliati, con quello vero accanto</h2>
      {numeri.length > 0 ? (
        numeri.map((a) => <Accostamento a={a} key={a.detto} />)
      ) : (
        <p className="vuota">Non controlliamo ancora i dati che dice. Quando lo faremo, qui vedrai quelli sbagliati con il dato vero accanto.</p>
      )}

      <p className="chiusura">
        Qui non diciamo se le {chi} idee sono buone o cattive. Diciamo cosa {s.tipo === "partito" ? "hanno detto e cosa hanno fatto" : "ha detto e cosa ha fatto"}. Il resto lo decidi tu.
      </p>
    </main>
  );
}

