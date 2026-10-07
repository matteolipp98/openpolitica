import type { Enunciato, Parametri, PosizioneSoggetto, Soggetto, Valore } from "../src/index.js";

export const PARAMETRI: Parametri = { pesoImportante: 2, margineParita: 3, sogliaNessunoTiRappresenta: 50 };

export const pos = (valore: Valore | null): PosizioneSoggetto => ({
  valore,
  stato: valore === null ? "non_documentata" : "documentata",
  confidenza: valore === null ? null : "piena",
});

export function soggetto(id: string, valori: (Valore | null)[], catalogo: Enunciato[]): Soggetto {
  return {
    id,
    nome: id,
    tipo: "partito",
    posizioni: Object.fromEntries(catalogo.map((e, i) => [e.id, pos(valori[i] ?? null)])),
  };
}

// Dati di adr/mockup/vista-questionario.html (inventati)
export const CATALOGO_MOCK: Enunciato[] = Array.from({ length: 8 }, (_, i) => ({ id: `d${i + 1}`, tema: `t${i + 1}` }));
const P: Record<string, (Valore | null)[]> = {
  "Alleanza Progresso": [-2, -1, 2, -2, 2, -1, -2, 1],
  "Civica Riformista": [1, 1, 1, 2, 0, 1, -1, -2],
  "Fronte dei Territori": [-2, -2, 1, -2, 2, -2, 2, 2],
  "Movimento Solidale": [2, 2, -2, 2, -2, 2, 2, -1],
  "Partito Lavoro e Comunità": [2, 2, -1, 1, -1, 2, 1, null],
  "Unione Liberale": [-2, -2, 2, 1, 2, -2, -2, -1],
  "Verdi e Territori": [2, 2, -1, 2, -2, 2, 1, -2],
  "Patto per le Regioni": [-1, -2, null, -1, 1, -1, 1, 2],
};
export const SOGGETTI_MOCK = Object.entries(P).map(([n, v]) => soggetto(n, v, CATALOGO_MOCK));
