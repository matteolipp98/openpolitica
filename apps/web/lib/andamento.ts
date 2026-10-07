// Andamento nel tempo (ADR 0040): dati pronti per le pagine, calcolati al build.
import { confrontoAnni, type Punto } from "@op/schema";
import { contenuto, pacchetto, parametri, partiti } from "./dati";
import type { MetricaTempo, Soggetto } from "./tipi";

interface TestiMetrica {
  id: MetricaTempo;
  nome: string;
  spiega: string;
  frase: string;
  notaGoverno?: string;
  notaOpposizione?: string;
  presto?: boolean;
}
interface TestiAndamento {
  confronto: Record<"piu" | "meno" | "uguale" | "pochi", string>;
  metriche: TestiMetrica[];
}

export const testiAndamento = () => contenuto<{ andamento: TestiAndamento }>("letture.yaml").andamento;
export const metricheTempo = () => testiAndamento().metriche;

const MESI = ["Gennaio – marzo", "Aprile – giugno", "Luglio – settembre", "Ottobre – dicembre"];
/** "2024-T2" → "Aprile – giugno 2024" */
export const nomeTrimestre = (t: string) => `${MESI[Number(t.slice(-1)) - 1]} ${t.slice(0, 4)}`;

export interface PuntoTempo extends Punto { governo: boolean }

export interface SchedaTempo {
  id: string;
  nome: string;
  ruolo: string;
  nota: string;
  cifra: string;
  frase: string;
  verdetto: string;
  prima: string;
  punti: PuntoTempo[];
}

const riempi = (t: string, n: number, d: number) => t.replace("{n}", String(n)).replace("{d}", String(d));

export function schedaTempo(s: Soggetto, m: TestiMetrica): SchedaTempo | null {
  const { andamento } = pacchetto();
  const serie = andamento.serie[s.id]?.[m.id];
  if (!serie) return null;
  const governo = andamento.governo[s.id] ?? serie.map(() => false);
  const minimo = parametri().presentazione.denominatoreMinimo;
  const c = confrontoAnni(serie, minimo);
  const oraAlGoverno = governo.at(-1) ?? false;
  const cambio = governo.findIndex((g, i) => i > 0 && g !== governo[i - 1]);
  const nota = [
    cambio > 0 && `${oraAlGoverno ? "È entrato nel governo" : "È uscito dal governo"} a ${nomeTrimestre(andamento.trimestri[cambio]!).split(" – ")[0]!.toLowerCase()} ${andamento.trimestri[cambio]!.slice(0, 4)}.`,
    oraAlGoverno && m.notaGoverno,
    !oraAlGoverno && m.notaOpposizione,
  ].filter(Boolean).join(" ");
  return {
    id: s.id,
    nome: s.nome,
    ruolo: s.ruolo,
    nota,
    cifra: c.ora.d >= minimo ? `${Math.round((c.ora.n / c.ora.d) * 100)}%` : "—",
    frase: `Nell'ultimo anno ${riempi(m.frase, c.ora.n, c.ora.d)}.`,
    verdetto: testiAndamento().confronto[c.verdetto],
    prima: `L'anno prima: ${c.prima.n} su ${c.prima.d}.`,
    punti: serie.map((p, i) => ({ ...p, governo: governo[i] ?? false })),
  };
}

/** Una scheda per partito, in ordine alfabetico (ADR 0009). */
export const schedeTempo = (m: TestiMetrica) =>
  partiti().map((s) => schedaTempo(s, m)).filter((x): x is SchedaTempo => x !== null);

export const trimestri = () => pacchetto().andamento.trimestri;
