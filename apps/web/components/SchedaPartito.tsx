// Scheda di un partito nella home (mock vista-soggetti, ADR 0036): chi lo guida, il programma per tema,
// tre voti uguali per tutti, due numeri con il loro totale.
import Link from "next/link";
import { Fragment } from "react";
import { alGiorno, alGoverno, conGoverno, quotaInParole, voto } from "@/lib/home";
import type { Domanda, Posizione, Soggetto, TemaPromessa } from "@/lib/tipi";

const fmt = (n: number) => n.toLocaleString("it-IT");

/** "A", "A e B", "A, B e C". */
const elenco = (x: string[]) => (x.length > 1 ? `${x.slice(0, -1).join(", ")} e ${x.at(-1)}` : (x[0] ?? ""));

export function SchedaPartito({ p, colore, temi, nomi, domande, posizioni, votiFino }: {
  p: Soggetto;
  colore: string;
  temi: { id: TemaPromessa; nome: string }[];
  nomi: Record<string, string>;
  domande: Domanda[];
  posizioni: Record<string, Posizione>;
  votiFino: string;
}) {
  const prog = p.programma;
  const anno = prog?.elezione.slice(0, 4);
  const conTemi = prog?.temi ? temi.map((t) => ({ ...t, n: prog.temi![t.id] ?? 0 })) : [];
  const max = Math.max(1, ...conTemi.map((t) => t.n));
  const conTema = conTemi.reduce((a, t) => a + t.n, 0);
  const gov = conGoverno(p.id);
  const governo = alGoverno(p);
  const stesso = (prog?.comune?.stesso_documento ?? []).map((s) => nomi[s] ?? s);
  const uguale = (prog?.comune?.testo_uguale ?? []).map((s) => nomi[s] ?? s);

  return (
    <article className="card scheda" id={p.slug}>
      <div className="testa">
        <span className="q" style={{ background: colore }} />
        <Link className="nome" href={`/partiti/${p.slug}`}>{p.nome}</Link>
        {p.guida && p.guida.length > 0 && (
          <span className="chi">
            Lo guida:{" "}
            {p.guida.map((g, i) => (
              <Fragment key={g.nome}>
                {i > 0 && (i === p.guida!.length - 1 ? " e " : ", ")}
                {g.slug ? <Link href={`/persone/${g.slug}`}>{g.nome}</Link> : g.nome}
              </Fragment>
            ))}
          </span>
        )}
        <span className="ruolo">{p.ruolo}</span>
      </div>

      <div className="blocco">
        <p className="et">Di cosa parla il suo programma{anno ? ` del ${anno}` : ""}</p>
        {!prog && <p className="vuoto">Non abbiamo ancora letto il suo programma.</p>}
        {prog && conTemi.length > 0 && (
          <ul className="temi">
            {conTemi.map((t) => (
              <li key={t.id}>
                <span>{t.nome}</span>
                <span className="barra"><i style={{ width: `${(100 * t.n) / max}%`, background: colore }} /></span>
                <span className="v">{fmt(t.n)}</span>
              </li>
            ))}
          </ul>
        )}
        {prog && conTemi.length === 0 && (
          <p className="vuoto">Stiamo ancora dividendo le promesse per tema. Il numero di promesse c&apos;è già.</p>
        )}
        {prog && conTemi.length > 0 && conTema < prog.promesse && (
          <p className="vuoto">Per {fmt(prog.promesse - conTema)} promesse il tema non c&apos;è ancora.</p>
        )}
        {stesso.length > 0 && (
          <p className="condiviso">È lo stesso programma di {elenco(stesso)}: nel {anno} hanno presentato un programma comune.</p>
        )}
        {uguale.length > 0 && (
          <p className="condiviso">Il testo è quasi tutto uguale a quello di {elenco(uguale)}: nel {anno} hanno presentato un programma comune.</p>
        )}
        {prog && (
          <details className="cosa">
            <summary>{fmt(prog.promesse)} promesse in tutto</summary>
            <p>Abbiamo letto tutto il programma che il partito ha depositato prima delle elezioni del {anno} e contato ogni impegno concreto, per esempio una legge, una spesa o un servizio nuovo. Ogni barra dice quante promesse parlano di quel tema. Più promesse non vuol dire promesse migliori.</p>
          </details>
        )}
      </div>

      {domande.length > 0 && (
        <div className="blocco">
          <p className="et">Come ha votato</p>
          <ul className="voti">
            {domande.map((d) => {
              const v = voto(posizioni[d.id]);
              return <li key={d.id}><span>{d.testo}</span><span className={v.classe}>{v.testo}</span></li>;
            })}
          </ul>
        </div>
      )}

      <div className="blocco numeri">
        {prog && (
          <div className="numero">
            <span className="c">{fmt(prog.precise.n)} <small>su {fmt(prog.precise.d)}</small></span>
            <p>promesse dicono quanto e entro quando<span className="s">Per esempio «20.000 insegnanti entro il 2027». Le altre sono più vaghe.</span></p>
          </div>
        )}
        {gov.d > 0 && (
          <div className="numero">
            <span className="c">{fmt(gov.n)} <small>su {fmt(gov.d)}</small></span>
            <p>leggi votate come il governo<span className="s">{governo ? "È al governo: è normale che voti quasi sempre così." : `Sono ${quotaInParole(gov.n, gov.d)} delle leggi votate finora.`}</span></p>
          </div>
        )}
      </div>

      <div className="piede">
        <span className="fonte">{anno ? `Programma ${anno} · ` : ""}voti fino {alGiorno(votiFino)}</span>
        <Link href={`/partiti/${p.slug}`}>Apri la scheda ›</Link>
      </div>
    </article>
  );
}
