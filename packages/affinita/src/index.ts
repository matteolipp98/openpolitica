// Algoritmo di affinità (ADR 0008, 0037). Puro e deterministico: stessi input, stesso risultato,
// in ogni browser. Usato dal questionario, dal test di equilibrio del catalogo e dai test.
// Cambiare il comportamento richiede di cambiare CALCOLO_VERSIONE e i casi in test/casi/.

export type Valore = -2 | -1 | 0 | 1 | 2;

export const CALCOLO_VERSIONE = "aff-1" as const;

export interface Enunciato { id: string; tema: string }
/** valore null = domanda saltata; 0 = "Non ho un'opinione". Entrambe non entrano nel calcolo. */
export interface Risposta { valore: Valore | null; importante: boolean }
export interface PosizioneSoggetto {
  /** null = posizione non documentata: non si stima mai (ADR 0008, 0030). */
  valore: Valore | null;
  stato: "documentata" | "non_documentata" | "divergente";
  confidenza: "piena" | "ridotta" | null;
}
export interface Soggetto {
  id: string;
  nome: string;
  tipo: "partito" | "persona" | "coalizione";
  posizioni: Readonly<Record<string, PosizioneSoggetto>>;
}
export interface Parametri {
  pesoImportante: number;
  margineParita: number;
  sogliaNessunoTiRappresenta: number;
}

export type Categoria = "concorde" | "discorde" | "neutrale" | "mancante";

export interface DettaglioDomanda {
  enunciatoId: string;
  categoria: Categoria;
  utente: Valore;
  soggetto: Valore | null;
  peso: number;
}

export interface RisultatoSoggetto {
  id: string;
  nome: string;
  /** Percentuale intera 0..100, oppure null se non c'è nessuna domanda confrontabile. */
  affinita: number | null;
  /** Domande a cui l'utente ha dato un'opinione. */
  risposte: number;
  concordi: string[];
  discordi: string[];
  neutrali: string[];
  mancanti: string[];
  /** Una voce per domanda con opinione, nell'ordine del catalogo. */
  dettaglio: DettaglioDomanda[];
}

export interface Risultato {
  soggetti: RisultatoSoggetto[];
  /** Soggetti alla pari in testa (entro margineParita dal primo). */
  primi: string[];
  nessunoTiRappresenta: boolean;
  calcoloVersione: typeof CALCOLO_VERSIONE;
}

const segno = (v: number) => (v > 0 ? 1 : v < 0 ? -1 : 0);
const confrontaId = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);

export function calcola(
  catalogo: readonly Enunciato[],
  risposte: Readonly<Record<string, Risposta>>,
  soggetti: readonly Soggetto[],
  par: Parametri,
): Risultato {
  const risultati = soggetti.map((s) => valuta(catalogo, risposte, s, par));
  // Affinità decrescente; a pari valore ordine per id, mai localeCompare (dipende dall'ambiente).
  risultati.sort((a, b) => (b.affinita ?? -1) - (a.affinita ?? -1) || confrontaId(a.id, b.id));

  const primo = risultati[0]?.affinita ?? null;
  const primi =
    primo === null
      ? []
      : risultati.filter((r) => r.affinita !== null && r.affinita >= primo - par.margineParita).map((r) => r.id);

  return {
    soggetti: risultati,
    primi,
    nessunoTiRappresenta: primo !== null && primo < par.sogliaNessunoTiRappresenta,
    calcoloVersione: CALCOLO_VERSIONE,
  };
}

function valuta(
  catalogo: readonly Enunciato[],
  risposte: Readonly<Record<string, Risposta>>,
  s: Soggetto,
  par: Parametri,
): RisultatoSoggetto {
  let punti = 0;
  let massimo = 0;
  let conOpinione = 0;
  const concordi: string[] = [];
  const discordi: string[] = [];
  const neutrali: string[] = [];
  const mancanti: string[] = [];
  const dettaglio: DettaglioDomanda[] = [];

  for (const e of catalogo) {
    const r = risposte[e.id];
    if (!r || r.valore === null || r.valore === 0) continue;
    const u = r.valore;
    const w = r.importante ? par.pesoImportante : 1;
    conOpinione++;

    const p = s.posizioni[e.id]?.valore ?? null;
    if (p === null) {
      mancanti.push(e.id);
      dettaglio.push({ enunciatoId: e.id, categoria: "mancante", utente: u, soggetto: null, peso: w });
      continue;
    }
    punti += (4 - Math.abs(u - p)) * w;
    massimo += 4 * w;
    const categoria: Categoria = p === 0 ? "neutrale" : segno(p) === segno(u) ? "concorde" : "discorde";
    (categoria === "concorde" ? concordi : categoria === "discorde" ? discordi : neutrali).push(e.id);
    dettaglio.push({ enunciatoId: e.id, categoria, utente: u, soggetto: p, peso: w });
  }

  return {
    id: s.id,
    nome: s.nome,
    affinita: massimo > 0 ? Math.round((100 * punti) / massimo) : null,
    risposte: conOpinione,
    concordi,
    discordi,
    neutrali,
    mancanti,
    dettaglio,
  };
}
