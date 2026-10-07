// Frasi generate da regole fisse e pubbliche (content/letture.yaml, ADR 0037). Uguali per tutti.
import { contenuto, parametri } from "./dati";
import type { Soggetto } from "./tipi";

interface Regole {
  frasiNumeri: { se?: string; altrimenti?: true; testo: string }[];
  letture: { metrica: string; verso?: "max" | "min"; aggregata?: boolean; testo: string; testoPiu?: string; sotto: string }[];
}

const regole = () => contenuto<Regole>("letture.yaml");
const minimo = () => parametri().presentazione.denominatoreMinimo;

function vale(cond: string, valori: Record<string, number>): boolean {
  const m = cond.match(/^(\w+)\s*(<=|>=|<|>)\s*([\d.]+)$/);
  if (!m) throw new Error(`regola non valida in letture.yaml: ${cond}`);
  const [, v, op, n] = m;
  const a = valori[v!]!, b = Number(n);
  return op === "<" ? a < b : op === "<=" ? a <= b : op === ">=" ? a >= b : a > b;
}

const riempi = (t: string, x: Record<string, string | number>) => t.replace(/\{(\w+)\}/g, (_, k) => String(x[k] ?? ""));

/** Frase sotto il nome di ogni soggetto, dai numeri controllati. */
export function fraseNumeri(s: Soggetto): string | null {
  if (!s.numeri) return null;
  const { sbagliati: n, controllati: d } = s.numeri;
  const valori = { denominatore: d, quota: d ? n / d : 0 };
  const r = regole().frasiNumeri.find((f) => f.altrimenti || vale(f.se!, valori))!;
  return riempi(r.testo, { n, d });
}

/** Cifra grande e testo del conteggio: sotto la soglia niente percentuale (ADR 0019). */
export function quota(n: number, d: number): { cifra: string; sotto: string; percentuale: boolean; pochi: string } {
  if (d < minimo()) return { cifra: String(n), sotto: `${n} su ${d}`, percentuale: false, pochi: " Sono ancora pochi per fare un confronto." };
  return { cifra: `${Math.round((n / d) * 100)}%`, sotto: `${n} su ${d}`, percentuale: true, pochi: "" };
}

export interface Lettura { cifra: string; testo: string; sotto: string; nomi: string[] }

const METRICHE: Record<string, (s: Soggetto) => { n: number; d: number } | null> = {
  numeri_sbagliati: (s) => (s.numeri ? { n: s.numeri.sbagliati, d: s.numeri.controllati } : null),
  non_controllabili: (s) => s.vaghi ?? null,
  voti_contrari: (s) => (s.coerenza ? { n: s.coerenza.contrari, d: s.coerenza.confrontabili } : null),
  promesse_non_mantenute: (s) => (s.promesse ? { n: s.promesse.totali - s.promesse.mantenute, d: s.promesse.totali } : null),
};

/** "In breve": una lettura per metrica, solo tra soggetti sopra soglia, pareggi nominati tutti (ADR 0037). */
export function letture(soggetti: Soggetto[]): Lettura[] {
  const out: Lettura[] = [];
  for (const l of regole().letture) {
    const valori = soggetti.map((s) => ({ s, c: METRICHE[l.metrica]!(s) })).filter((x) => x.c);
    if (l.aggregata) {
      const n = valori.reduce((a, x) => a + x.c!.n, 0), d = valori.reduce((a, x) => a + x.c!.d, 0);
      if (d) out.push({ cifra: String(n), testo: riempi(l.testo, { n, d }), sotto: riempi(l.sotto, { n, d }), nomi: [] });
      continue;
    }
    const ammessi = valori.filter((x) => x.c!.d >= minimo());
    if (ammessi.length < 2) continue;
    const q = (x: (typeof ammessi)[number]) => x.c!.n / x.c!.d;
    const estremo = l.verso === "min" ? Math.min(...ammessi.map(q)) : Math.max(...ammessi.map(q));
    const vincitori = ammessi.filter((x) => q(x) === estremo);
    const nomi = vincitori.map((x) => x.s.nome);
    const { n, d } = vincitori[0]!.c!;
    const testo = vincitori.length > 1 && l.testoPiu ? l.testoPiu : l.testo;
    out.push({
      cifra: l.metrica === "non_controllabili" ? `${Math.round((n / d) * 100)}%` : String(n),
      testo: riempi(testo, { soggetti: nomi.join(" e "), n, d }),
      sotto: riempi(l.sotto, { n, d }),
      nomi,
    });
  }
  return out;
}
