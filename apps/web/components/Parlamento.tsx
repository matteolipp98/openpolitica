// "Il Parlamento oggi" (mock vista-soggetti, ADR 0036). L'emiciclo è un SVG fatto al build; il selettore
// Camera/Senato funziona senza JavaScript: due caselle di scelta nascoste e i loro due riquadri.
import { Fragment } from "react";
import { NOME_RAMO, alGiorno, alGoverno, posti, quotaInParole } from "@/lib/home";
import type { Parlamento as P, Ramo, Soggetto } from "@/lib/tipi";

const fmt = (n: number) => n.toLocaleString("it-IT");
const MISTO = "var(--rule)";

function Ramo({ ramo, dati, partiti, colore, data }: {
  ramo: Ramo; dati: NonNullable<P["rami"][Ramo]>; partiti: Soggetto[]; colore: Record<string, string>; data: string;
}) {
  const { totale, altri } = dati;
  const seggi = (p: Soggetto) => dati.partiti[p.id] ?? 0;
  const conSeggi = partiti.filter((p) => seggi(p) > 0);
  const gov = conSeggi.filter(alGoverno), opp = conSeggi.filter((p) => !alGoverno(p));
  const nGov = gov.reduce((a, p) => a + seggi(p), 0);
  // Prima l'opposizione, poi il gruppo misto, poi il governo; dentro ogni gruppo in ordine alfabetico
  const blocchi: [string, number][] = [...opp.map((p) => [colore[p.id]!, seggi(p)] as [string, number]), [MISTO, altri],
    ...gov.map((p) => [colore[p.id]!, seggi(p)] as [string, number])];
  const colori = blocchi.flatMap(([c, n]) => Array<string>(n).fill(c));
  const r = totale > 300 ? 4.6 : 6.4;
  const { chi, fonte } = NOME_RAMO[ramo];
  const riga = (p: Soggetto) => (
    <li key={p.id}><span className="q" style={{ background: colore[p.id] }} /><span>{p.nome}</span><span className="n">{fmt(seggi(p))}</span></li>
  );
  return (
    <div className={`ramo ramo-${ramo}`}>
      <div className="aula-griglia">
        <div>
          <svg className="emiciclo" viewBox="0 0 400 206" role="img" aria-label={`Seggi per partito: ${fmt(totale)} ${chi}`}>
            {posti(totale).map((p, i) => (
              <circle key={i} cx={p.x.toFixed(1)} cy={p.y.toFixed(1)} r={r} fill={colori[i]} />
            ))}
          </svg>
          <div className="emi-et"><span>All&apos;opposizione</span><span>Al governo</span></div>
        </div>
        <div>
          <div className="grande">{fmt(nGov)}<small>su {fmt(totale)} {chi}</small></div>
          <p className="frase-grande">sostengono il governo: sono {quotaInParole(nGov, totale)}.</p>
          <div className="divisa" aria-hidden="true">
            {blocchi.filter(([, n]) => n > 0).map(([c, n], i) => (
              <span key={i} style={{ width: `${(100 * n) / totale}%`, background: c }} />
            ))}
          </div>
          <div className="divisa-et"><span>Opposizione e misto: {fmt(totale - nGov)}</span><span>Governo: {fmt(nGov)}</span></div>
          <ul className="legenda">
            <li className="gruppo">Al governo</li>
            {gov.map(riga)}
            <li className="gruppo">All&apos;opposizione</li>
            {opp.map(riga)}
            {altri > 0 && (
              <li><span className="q" style={{ background: MISTO }} /><span>Gruppo misto e altri</span><span className="n">{fmt(altri)}</span></li>
            )}
          </ul>
        </div>
      </div>
      <div className="fonte">Fonte: {fonte} · aggiornato {alGiorno(data)}</div>
    </div>
  );
}

export function Parlamento({ dati, partiti, colore }: { dati: P; partiti: Soggetto[]; colore: Record<string, string> }) {
  const rami = (["camera", "senato"] as const).filter((r) => dati.rami[r]);
  return (
    <section className="card aula" aria-labelledby="titolo-aula">
      {rami.map((r, i) => (
        <input key={r} className="nascosto" type="radio" name="ramo" id={`ramo-${r}`} defaultChecked={i === 0} />
      ))}
      <div className="tabs">
        {rami.map((r) => <label key={r} htmlFor={`ramo-${r}`}>{NOME_RAMO[r].ramo}</label>)}
      </div>
      {rami.map((r) => (
        <Fragment key={r}>
          <Ramo ramo={r} dati={dati.rami[r]!} partiti={partiti} colore={colore} data={dati.data} />
        </Fragment>
      ))}
      <details className="cosa">
        <summary>Come leggere il disegno</summary>
        <p>Ogni pallino è un parlamentare. I pallini sono messi in due gruppi, opposizione e governo, e dentro ogni gruppo in ordine alfabetico. Non è la disposizione reale dell&apos;aula.</p>
        <p>Contiamo i parlamentari in carica oggi, con il gruppo in cui stanno adesso. Chi sta nel gruppo misto, o in un partito che non seguiamo, è contato a parte: «gruppo misto e altri».</p>
      </details>
    </section>
  );
}
