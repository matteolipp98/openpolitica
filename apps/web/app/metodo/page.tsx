import type { Metadata } from "next";
import Link from "next/link";
import { equilibrio, type Soggetto as SoggettoAffinita } from "@op/affinita";
import { NotaEsempio } from "@/components/NotaEsempio";
import { Segnala } from "@/components/Segnala";
import { contenuto, pacchetto, parametri, partiti } from "@/lib/dati";

export const metadata: Metadata = { title: "Il metodo" };

const MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];
const inParole = (iso: string) => {
  const [a, m, g] = iso.split("-").map(Number);
  return `${g} ${MESI[m! - 1]} ${a}`;
};
const NUMERI = ["nessuna", "una", "due", "tre", "quattro", "cinque", "sei", "sette", "otto", "nove", "dieci"];
const aParole = (n: number) => NUMERI[n] ?? String(n);

/** Prova di imparzialità sulle domande pubblicate, calcolata al build come nel workflow Rilascio (piano §3.11). */
function prova(): { fatta: false } | { fatta: true; superata: boolean; n: number } {
  const { domande, posizioni } = pacchetto();
  if (domande.length === 0) return { fatta: false };
  const ps = partiti();
  const soggetti: SoggettoAffinita[] = ps.map((p) => ({
    id: p.id,
    nome: p.nome,
    tipo: "partito",
    posizioni: Object.fromEntries(
      Object.entries(posizioni[p.id] ?? {}).map(([k, v]) => [k, { valore: v.valore, stato: v.stato, confidenza: v.valore === null ? null : "piena" as const }]),
    ),
  }));
  const aree = Object.fromEntries(ps.map((p) => [p.id, /opposizione/i.test(p.ruolo) ? "opposizione" : /governo/i.test(p.ruolo) ? "governo" : "altro"]));
  const par = parametri();
  const r = equilibrio(domande, soggetti, aree, par.affinita, par.equilibrio);
  return { fatta: true, superata: r.problemi.length === 0, n: r.n };
}

const FONTI: [string, string, string | null][] = [
  ["Voti della Camera", "dati.camera.it, pubblici", "camera"],
  ["Voti del Senato", "dati.senato.it, pubblici", "senato"],
  ["Programmi elettorali", "Ministero dell'Interno", null],
  ["Cosa dicono i politici", "discorsi in Parlamento, siti dei partiti, notizie", null],
  ["Dati ufficiali per controllare i numeri", "ISTAT, Eurostat, Banca d'Italia", null],
];

export default function Metodo() {
  const { domande, manifest, correzioni } = pacchetto();
  const temi = contenuto<{ temi: { id: string }[] }>("temi.yaml").temi;
  const conti = temi.map((t) => domande.filter((d) => d.tema === t.id).length);
  const uguali = domande.length > 0 && conti.every((c) => c === conti[0]);
  const p = prova();
  const base = process.env.NEXT_PUBLIC_SUPABASE_URL?.replace(/\/$/, "");
  const scarica = !manifest.esempio && base ? `${base}/storage/v1/object/public/rilasci/${manifest.versione}/manifest.json` : null;

  return (
    <main>
      <h1>Il metodo, nel dettaglio</h1>
      <p className="lede">
        Qui spieghiamo come lavoriamo, con più dettagli. Se ti basta l&apos;idea generale, leggi <Link href="/come-funziona">Come funziona</Link>.
      </p>
      <NotaEsempio />

      <h2 id="domande">Come scegliamo le domande</h2>
      {[
        ["Partiamo dai voti veri", "Prendiamo le votazioni finali in Parlamento in cui i partiti si sono divisi davvero: almeno uno su quattro ha votato dall'altra parte."],
        ["Un programma scrive la domanda", "Un sistema di intelligenza artificiale trasforma la legge votata in una frase semplice, a cui si risponde sì o no."],
        ["Un secondo controllo, alla cieca", "Una seconda richiesta, separata, rilegge la domanda senza sapere com'è nata. Se le due non vanno d'accordo, la domanda si butta."],
        ["Lo stesso numero per ogni tema", uguali
          ? `Così nessun argomento pesa più degli altri. Oggi sono ${domande.length} domande, ${aParole(conti[0]!)} per ognuno dei ${aParole(temi.length)} temi.`
          : `Così nessun argomento pesa più degli altri.${domande.length ? ` Oggi sono ${domande.length} domande.` : ""}`],
      ].map(([t, d], i) => (
        <div className="passo" key={t}>
          <span className="num">{i + 1}</span>
          <div><h3>{t}</h3><p>{d}</p></div>
        </div>
      ))}

      <div className="box">
        <p><b>La prova dell&apos;imparzialità.</b> Facciamo rispondere al questionario {p.fatta ? p.n.toLocaleString("it-IT") : "20.000"} persone simulate, a caso. Se le domande fossero sbilanciate, un partito uscirebbe primo molto più spesso degli altri.</p>
        <p className="esito-prova">
          {!p.fatta ? "Le domande non ci sono ancora: faremo la prova appena arrivano." : p.superata ? "Prova superata: nessuno schieramento esce favorito." : "Prova non superata: queste domande vanno rifatte."}
        </p>
        <p>Rifacciamo la prova ogni volta che cambiano le domande. Se non la superano, non le pubblichiamo.</p>
      </div>
      {manifest.catalogo.stato === "provvisorio" && (
        <div className="box">
          <p><b>Il nostro limite.</b> Per ora le domande le scrive e le controlla un solo sistema di intelligenza artificiale. Per questo le chiamiamo <i>provvisorie</i>: quando avremo un secondo sistema, le ricontrolleremo tutte.</p>
        </div>
      )}

      <h2 id="dati">Da dove vengono i dati</h2>
      <div className="fonti">
        {FONTI.map(([nome, dove, ramo]) => {
          const fino = ramo ? manifest.fonti?.[ramo]?.ultima_votazione : undefined;
          return (
            <div className="fonte" key={nome}>
              <div className="nome">{nome}<span>{dove}</span></div>
              <div className={`fin${fino ? "" : " no"}`}>{fino ? `fino al ${inParole(fino)}` : ramo && manifest.esempio ? "—" : "arriva presto"}</div>
            </div>
          );
        })}
      </div>
      {!manifest.esempio && <p>Stiamo ancora caricando i voti: ogni giorno arrivano quelli che mancano.</p>}
      <p>
        Tutto quello che pubblichiamo si può scaricare e controllare. Versione di oggi:{" "}
        {scarica ? <a href={scarica}>{manifest.versione}</a> : manifest.versione}.
      </p>

      <h2 id="correzioni">Correzioni</h2>
      <p>Quando sbagliamo lo scriviamo qui, con la data e cosa abbiamo cambiato. Non cancelliamo niente di nascosto.</p>
      {correzioni.length === 0 ? (
        <div className="box"><p className="vuoto">Finora nessuna correzione.</p></div>
      ) : (
        <div className="fonti">
          {correzioni.map((c) => (
            <div className="correzione" key={`${c.quando}-${c.oggetto}`}>
              <p className="quando">{inParole(c.quando)}</p>
              <p>{c.motivo}</p>
              <p className="sotto">Prima: {c.prima}. Ora: {c.dopo}.</p>
            </div>
          ))}
        </div>
      )}
      <Segnala dove="/metodo" />
    </main>
  );
}
