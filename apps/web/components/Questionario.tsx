"use client";
import { calcola, type Parametri, type Risposta, type Soggetto, type Valore } from "@op/affinita";
import { useEffect, useMemo, useState } from "react";
import type { Domanda } from "@/lib/tipi";

const CHIAVE = "op.profilo.v1";
const NUMERI = ["Zero", "Una", "Due", "Tre", "Quattro", "Cinque", "Sei", "Sette", "Otto", "Nove", "Dieci"];

interface Props {
  domande: Domanda[];
  soggetti: (Soggetto & { ruolo: string })[];
  parametri: Parametri;
  catalogo: string;
}

interface Profilo { catalogo: string; risposte: Record<string, Risposta>; i: number }

/** Le risposte restano sul dispositivo (ADR 0007): localStorage, mai inviate. Se non si può salvare, si prosegue. */
function carica(catalogo: string): Profilo | null {
  try {
    const p = JSON.parse(localStorage.getItem(CHIAVE) ?? "null") as Profilo | null;
    return p && p.catalogo === catalogo ? p : null;
  } catch {
    return null;
  }
}
function salva(p: Profilo) {
  try { localStorage.setItem(CHIAVE, JSON.stringify(p)); } catch { /* modalità privata */ }
}
function cancella() {
  try { localStorage.removeItem(CHIAVE); } catch { /* niente da fare */ }
}

export function Questionario({ domande, soggetti, parametri, catalogo }: Props) {
  const [risposte, setRisposte] = useState<Record<string, Risposta>>({});
  const [i, setI] = useState(0);
  const [importante, setImportante] = useState(false);

  useEffect(() => {
    const p = carica(catalogo);
    if (p) { setRisposte(p.risposte); setI(p.i); }
  }, [catalogo]);

  const rispondi = (valore: Valore) => {
    const d = domande[i]!;
    const nuove = { ...risposte, [d.id]: { valore, importante } };
    setRisposte(nuove);
    setImportante(false);
    setI(i + 1);
    salva({ catalogo, risposte: nuove, i: i + 1 });
    window.scrollTo(0, 0);
  };
  const indietro = () => { setI(i - 1); setImportante(!!risposte[domande[i - 1]!.id]?.importante); };
  const rifai = () => { cancella(); setRisposte({}); setI(0); window.scrollTo(0, 0); };

  const risultato = useMemo(
    () => (i >= domande.length ? calcola(domande, risposte, soggetti, parametri) : null),
    [i, domande, risposte, soggetti, parametri],
  );
  const testoDi = (id: string) => domande.find((d) => d.id === id)?.testo ?? id;

  if (!risultato) {
    const d = domande[i]!;
    return (
      <>
        <p className="lede">{NUMERI[domande.length] ?? domande.length} domande. Poi ti diciamo chi ha votato come la pensi tu, e su cosa invece non siete d&apos;accordo.</p>
        <div className="avanz" aria-hidden="true">{domande.map((x, k) => <i key={x.id} className={k < i ? "on" : ""} />)}</div>
        <div className="box">
          <p className="conta">Domanda {i + 1} di {domande.length}</p>
          <p className="dom">{d.testo}</p>
          <div className="contesto">
            <p><b>Prima di rispondere:</b> {d.contesto.fatto}</p>
            {d.contesto.favorevoli && <p>{d.contesto.favorevoli}</p>}
            {d.contesto.contrari && <p>{d.contesto.contrari}</p>}
          </div>
          <div className="scelte">
            <button type="button" onClick={() => rispondi(2)}>Sono d&apos;accordo</button>
            <button type="button" onClick={() => rispondi(-2)}>Sono contrario</button>
            <button type="button" onClick={() => rispondi(0)}>Non ho un&apos;opinione</button>
          </div>
          <label className="conta-imp">
            <input type="checkbox" checked={importante} onChange={(e) => setImportante(e.target.checked)} />
            Questo argomento per me conta più degli altri
          </label>
          {i > 0 && <button className="indietro" type="button" onClick={indietro}>← Torna indietro</button>}
        </div>
      </>
    );
  }

  const primo = risultato.soggetti[0]!;
  const ruolo = (id: string) => soggetti.find((s) => s.id === id)?.ruolo ?? "";
  if (primo.affinita === null)
    return (
      <>
        <div className="avviso"><b>Così non possiamo dirti niente.</b> Hai risposto &quot;non ho un&apos;opinione&quot; a tutto. Prova a rispondere almeno a qualche domanda.</div>
        <button className="rifai" type="button" onClick={rifai}>Rifai le domande</button>
      </>
    );
  const pari = risultato.primi.map((id) => risultato.soggetti.find((s) => s.id === id)!);
  return (
    <>
      {risultato.nessunoTiRappresenta && (
        <div className="avviso"><b>Nessuno la pensa davvero come te.</b> Il più vicino è d&apos;accordo con te solo su {primo.concordi.length} domande su {domande.length}. Succede, e non è un errore tuo: vuol dire che le tue idee non stanno tutte dentro un partito solo.</div>
      )}
      <div className="vinc">
        <p className="et">{pari.length > 1 ? "Sono alla pari" : "Il più vicino a te"}</p>
        <h2>{pari.map((p) => p.nome).join(" · ")}</h2>
        <p className="pct">{primo.affinita}%</p>
        <p className="sotto">D&apos;accordo con te su {primo.concordi.length} domande su {domande.length}. Non d&apos;accordo su {primo.discordi.length}.</p>
      </div>
      {risultato.soggetti.map((s) => (
        <details className="r" key={s.id}>
          <summary>
            <span className="p">{s.affinita === null ? "—" : `${s.affinita}%`}</span>
            <span className="nm"><b>{s.nome}</b><span>{ruolo(s.id)} · d&apos;accordo su {s.concordi.length} di {domande.length}</span></span>
            <span className="apri" style={{ margin: 0, fontSize: 14 }}><span className="chiuso">vedi ▾</span><span className="aperto">chiudi ▴</span></span>
          </summary>
          <div className="barra"><i style={{ width: `${s.affinita ?? 0}%` }} /></div>
          <div className="dett">
            {s.concordi.length > 0 && <><h3>Su queste cose siete d&apos;accordo</h3>{s.concordi.map((k) => <div className="pt ok" key={k}><b>Sì</b><span>{testoDi(k)}</span></div>)}</>}
            {s.discordi.length > 0 && <><h3>Su queste no</h3>{s.discordi.map((k) => <div className="pt no" key={k}><b>No</b><span>{testoDi(k)}</span></div>)}</>}
            {s.neutrali.length > 0 && <><h3>Su queste non hanno scelto</h3>{s.neutrali.map((k) => <div className="pt" key={k}><b>Né sì né no</b><span>{testoDi(k)}</span></div>)}</>}
            {s.affinita === null && <p className="vuoto">Non sappiamo come hanno votato sulle tue domande.</p>}
            {s.mancanti.length > 0 && <p className="vuoto">Su {s.mancanti.length} domande non abbiamo trovato nessun voto: non inventiamo la loro posizione.</p>}
            <p className="vuoto">Ogni &quot;sì&quot; o &quot;no&quot; viene da un voto in Parlamento. Nella scheda del partito vedi quale legge e quando.</p>
          </div>
        </details>
      ))}
      <button className="rifai" type="button" onClick={rifai}>Rifai le domande</button>
      <p className="vuoto">Il risultato viene da una formula fissa, uguale per tutti. Non è un consiglio di voto.</p>
    </>
  );
}
