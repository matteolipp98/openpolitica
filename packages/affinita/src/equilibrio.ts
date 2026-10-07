// Test di equilibrio del catalogo (piano §3.11, ADR 0006, 0022). Simula molte persone che rispondono al
// questionario e controlla che le domande non premino uno schieramento per come sono costruite.
// Puro e con seme fisso: stesso catalogo, stesso rapporto.
import { calcola, type Enunciato, type Parametri, type Soggetto, type Valore } from "./index.js";
import { mulberry32 } from "./prng.js";

export interface Soglie {
  /** Affinità media di ogni soggetto entro ± questo scarto da 50, con risposte a caso. */
  scartoAffinitaMedia: number;
  /** Quota di primi posti di ogni area entro ± questi punti dalla quota di soggetti dell'area. */
  scartoQuotaPrimi: number;
  /** Con risposte "di area", l'area deve risultare prima almeno in questa quota di casi. */
  riconoscimentoArea: number;
}

export interface RapportoEquilibrio {
  n: number;
  seme: number;
  affinitaMedia: Record<string, number>;
  quotaPrimiPerArea: Record<string, number>;
  quotaSoggettiPerArea: Record<string, number>;
  riconoscimentoArea: Record<string, number>;
  /** Vuoto = test superato. Ogni voce dice cosa non va, con i numeri. */
  problemi: string[];
}

const PULSANTI: Valore[] = [2, -2, 0]; // "d'accordo", "contrario", "non ho un'opinione": stessa probabilità

function acaso(rnd: () => number): Valore {
  return PULSANTI[Math.floor(rnd() * 3)]!;
}

function profiloDiArea(
  catalogo: readonly Enunciato[], medie: Record<string, number>, rnd: () => number, fedelta = 0.8,
): Record<string, { valore: Valore; importante: boolean }> {
  return Object.fromEntries(catalogo.map((e) => {
    const m = medie[e.id] ?? 0;
    const valore: Valore = m !== 0 && rnd() < fedelta ? (m > 0 ? 2 : -2) : acaso(rnd);
    return [e.id, { valore, importante: rnd() < 0.2 }];
  }));
}

export function equilibrio(
  catalogo: readonly Enunciato[],
  soggetti: readonly Soggetto[],
  aree: Readonly<Record<string, string>>,
  par: Parametri,
  soglie: Soglie,
  n = 20_000,
  seme = 42,
): RapportoEquilibrio {
  const rnd = mulberry32(seme);
  const problemi: string[] = [];
  const nomiAree = [...new Set(soggetti.map((s) => aree[s.id] ?? "altro"))].sort();
  const quotaSoggettiPerArea = Object.fromEntries(
    nomiAree.map((a) => [a, soggetti.filter((s) => (aree[s.id] ?? "altro") === a).length / soggetti.length]),
  );

  // 1 e 2: risposte a caso, uguali per tutti i pulsanti
  const somma = new Map<string, number>();
  const conti = new Map<string, number>();
  const primiArea = new Map<string, number>();
  for (let i = 0; i < n; i++) {
    const risposte = Object.fromEntries(catalogo.map((e) => [e.id, { valore: acaso(rnd), importante: rnd() < 0.2 }]));
    const r = calcola(catalogo, risposte, soggetti, par);
    for (const id of r.primi) {
      const a = aree[id] ?? "altro";
      primiArea.set(a, (primiArea.get(a) ?? 0) + 1 / r.primi.length);
    }
    for (const s of r.soggetti)
      if (s.affinita !== null) {
        somma.set(s.id, (somma.get(s.id) ?? 0) + s.affinita);
        conti.set(s.id, (conti.get(s.id) ?? 0) + 1);
      }
  }
  const affinitaMedia = Object.fromEntries([...somma].map(([id, v]) => [id, Math.round((v / conti.get(id)!) * 10) / 10]));
  for (const [id, m] of Object.entries(affinitaMedia))
    if (Math.abs(m - 50) > soglie.scartoAffinitaMedia)
      problemi.push(`${id}: affinità media ${m} con risposte a caso, attesa 50 ± ${soglie.scartoAffinitaMedia}`);
  const quotaPrimiPerArea = Object.fromEntries(nomiAree.map((a) => [a, Math.round(((primiArea.get(a) ?? 0) / n) * 1000) / 1000]));
  for (const a of nomiAree) {
    const scarto = Math.abs(quotaPrimiPerArea[a]! - quotaSoggettiPerArea[a]!) * 100;
    if (scarto > soglie.scartoQuotaPrimi)
      problemi.push(
        `${a}: prima nel ${Math.round(quotaPrimiPerArea[a]! * 100)}% dei casi con risposte a caso, ` +
          `ma è il ${Math.round(quotaSoggettiPerArea[a]! * 100)}% dei soggetti (scarto massimo ${soglie.scartoQuotaPrimi} punti)`,
      );
  }

  // 3: risposte "di area", attorno alle posizioni medie di ogni area
  const riconoscimentoArea: Record<string, number> = {};
  const nArea = Math.max(1, Math.round(n / Math.max(1, nomiAree.length)));
  for (const a of nomiAree) {
    const membri = soggetti.filter((s) => (aree[s.id] ?? "altro") === a);
    const medie: Record<string, number> = {};
    for (const e of catalogo) {
      const v = membri.map((s) => s.posizioni[e.id]?.valore).filter((x): x is Valore => x !== null && x !== undefined);
      medie[e.id] = v.length ? v.reduce((x: number, y) => x + y, 0) / v.length : 0;
    }
    let vinte = 0;
    for (let i = 0; i < nArea; i++) {
      const r = calcola(catalogo, profiloDiArea(catalogo, medie, rnd), soggetti, par);
      vinte += r.primi.filter((id) => (aree[id] ?? "altro") === a).length / Math.max(1, r.primi.length);
    }
    riconoscimentoArea[a] = Math.round((vinte / nArea) * 1000) / 1000;
    if (riconoscimentoArea[a]! < soglie.riconoscimentoArea)
      problemi.push(
        `${a}: chi la pensa come quest'area la trova prima solo nel ${Math.round(riconoscimentoArea[a]! * 100)}% dei casi ` +
          `(minimo ${Math.round(soglie.riconoscimentoArea * 100)}%): le domande non distinguono abbastanza le aree`,
      );
  }

  return { n, seme, affinitaMedia, quotaPrimiPerArea, quotaSoggettiPerArea, riconoscimentoArea, problemi };
}
