// Regole fisse della home (ADR 0036, "Indice dei soggetti"; issue #76). Uguali per tutti i partiti.
import { pacchetto } from "./dati";
import type { Domanda, Posizione, Ramo, Soggetto } from "./tipi";

const MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];

/** "2026-10-06" → "6 ottobre 2026". */
export function inParole(iso: string): string {
  const [a, m, g] = iso.split("-").map(Number);
  return `${g} ${MESI[m! - 1]} ${a}`;
}

/** "al 6 ottobre 2026", "all'8 ottobre 2026". */
export function alGiorno(iso: string): string {
  const g = Number(iso.slice(8, 10));
  return `${g === 8 || g === 11 ? "all'" : "al "}${inParole(iso)}`;
}

/** Confronti concreti al posto delle percentuali (ADR 0036). */
export function quotaInParole(n: number, d: number): string {
  const q = d ? n / d : 0;
  if (q > 0.95) return "quasi tutti";
  if (q > 0.66) return "più di due su tre";
  if (q > 0.5) return "più della metà";
  if (q > 0.33) return "più di un terzo";
  if (q > 0.25) return "più di un quarto";
  return "meno di un quarto";
}

export const alGoverno = (s: Soggetto) => s.ruolo === "Al governo";

/** Colori neutri assegnati in ordine alfabetico, mai quelli dei simboli (ADR 0009). */
export function colori(partiti: Soggetto[]): Record<string, string> {
  return Object.fromEntries(partiti.map((p, i) => [p.id, `var(--p${(i % 10) + 1})`]));
}

/** Le tre domande votate più di recente, su tre temi diversi: le stesse per tutti i partiti. */
export function domandeHome(domande: Domanda[], quante = 3): Domanda[] {
  const ordinate = domande
    .filter((d) => d.data)
    .sort((a, b) => b.data!.localeCompare(a.data!) || a.id.localeCompare(b.id));
  const out: Domanda[] = [];
  for (const d of ordinate) {
    if (out.length === quante) break;
    if (!out.some((x) => x.tema === d.tema)) out.push(d);
  }
  return out;
}

/** Come ha votato un partito sulla frase della domanda: Sì, No, Né sì né no, oppure non si sa. */
export function voto(p?: Posizione): { testo: string; classe: "v-si" | "v-no" | "v-ast" } {
  if (!p || p.valore === null) return { testo: "Non si sa", classe: "v-ast" };
  if (p.valore > 0) return { testo: "Sì", classe: "v-si" };
  if (p.valore < 0) return { testo: "No", classe: "v-no" };
  return { testo: "Né sì né no", classe: "v-ast" };
}

/** Leggi votate come il governo, sommando tutti i trimestri (metrica vota_con_governo, ADR 0040). */
export function conGoverno(id: string): { n: number; d: number } {
  const serie = pacchetto().andamento.serie[id]?.vota_con_governo ?? [];
  return { n: serie.reduce((a, p) => a + p.n, 0), d: serie.reduce((a, p) => a + p.d, 0) };
}

/** Fin dove arrivano i voti: il ramo più indietro. Nei dati di esempio, il giorno del pacchetto. */
export function votiFinoAl(): string {
  const { manifest } = pacchetto();
  const date = Object.values(manifest.fonti ?? {}).map((f) => f.ultima_votazione).sort();
  return date[0] ?? manifest.generato_il;
}

export const NOME_RAMO: Record<Ramo, { ramo: string; fonte: string; chi: string }> = {
  camera: { ramo: "Camera", fonte: "Camera dei deputati", chi: "deputati" },
  senato: { ramo: "Senato", fonte: "Senato della Repubblica", chi: "senatori" },
};

/**
 * Posizioni dei pallini dell'emiciclo su righe concentriche, da sinistra a destra.
 * Disegno nel riquadro 400 × 206, centro in basso (200, 198).
 */
export function posti(totale: number): { x: number; y: number }[] {
  const righe = Math.max(4, Math.round(Math.sqrt(totale / 1.6)));
  const R = 190, r0 = 72;
  const raggi = Array.from({ length: righe }, (_, i) => r0 + ((R - r0) * i) / (righe - 1));
  const lungh = raggi.reduce((a, r) => a + r, 0);
  let resto = totale;
  const pts: { a: number; x: number; y: number }[] = [];
  raggi.forEach((r, i) => {
    const n = i === righe - 1 ? resto : Math.round((totale * r) / lungh);
    resto -= n;
    for (let k = 0; k < n; k++) {
      const a = Math.PI * (1 - (k + 0.5) / n);
      pts.push({ a, x: 200 + r * Math.cos(a), y: 198 - r * Math.sin(a) });
    }
  });
  return pts.sort((p, q) => q.a - p.a);
}
