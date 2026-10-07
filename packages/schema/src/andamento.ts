// Frase anno contro anno dell'andamento nel tempo (ADR 0040). Regola fissa e pubblica:
// si sommano gli ultimi quattro trimestri e i quattro precedenti; "più" o "meno" solo se gli
// intervalli di Wilson al 95% non si sovrappongono, altrimenti "uguale"; "pochi" se un anno è sotto soglia.

export interface Punto { n: number; d: number }
export type Verdetto = "piu" | "meno" | "uguale" | "pochi";

const Z = 1.96;

export function wilson(n: number, d: number): [number, number] {
  if (d === 0) return [0, 1];
  const p = n / d, den = 1 + (Z * Z) / d, c = p + (Z * Z) / (2 * d);
  const m = Z * Math.sqrt((p * (1 - p)) / d + (Z * Z) / (4 * d * d));
  return [(c - m) / den, (c + m) / den];
}

const somma = (a: Punto[]): Punto => a.reduce((x, y) => ({ n: x.n + y.n, d: x.d + y.d }), { n: 0, d: 0 });

export function confrontoAnni(serie: Punto[], minimo: number): { ora: Punto; prima: Punto; verdetto: Verdetto } {
  const ora = somma(serie.slice(-4)), prima = somma(serie.slice(-8, -4));
  if (serie.length < 8 || ora.d < minimo || prima.d < minimo) return { ora, prima, verdetto: "pochi" };
  const [aBasso, aAlto] = wilson(ora.n, ora.d), [bBasso, bAlto] = wilson(prima.n, prima.d);
  const verdetto = aBasso > bAlto ? "piu" : aAlto < bBasso ? "meno" : "uguale";
  return { ora, prima, verdetto };
}
