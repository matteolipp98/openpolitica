import { describe, expect, it } from "vitest";
import { calcola, type Risposta, type Valore } from "../src/index.js";
import { CATALOGO_MOCK, PARAMETRI, SOGGETTI_MOCK, soggetto } from "./dati.js";

const risposte = (valori: (Valore | null)[], importanti: number[] = []): Record<string, Risposta> =>
  Object.fromEntries(valori.map((v, i) => [`d${i + 1}`, { valore: v, importante: importanti.includes(i) }]));

describe("caso calcolato a mano", () => {
  const cat = [{ id: "d1", tema: "a" }, { id: "d2", tema: "a" }, { id: "d3", tema: "b" }, { id: "d4", tema: "b" }];
  // utente: +2, -2, +2 (importante), 0  →  la d4 non conta
  const r = risposte([2, -2, 2, 0], [2]);

  it("somma i punti 4-|u-p| pesati e divide per il massimo", () => {
    // A: d1 p=+2 → 4·1; d2 p=+1 → (4-3)·1 = 1; d3 p=-2 → 0·2  ⇒ 5 / (4+4+8) = 31%
    const A = soggetto("A", [2, 1, -2, 2], cat);
    const [ris] = calcola(cat, r, [A], PARAMETRI).soggetti;
    expect(ris!.affinita).toBe(31);
    expect(ris!.concordi).toEqual(["d1"]);
    expect(ris!.discordi).toEqual(["d2", "d3"]);
    expect(ris!.risposte).toBe(3);
  });

  it("posizione 0 è neutrale, non disaccordo (ADR 0037)", () => {
    const B = soggetto("B", [0, 0, 0, 0], cat);
    const [ris] = calcola(cat, r, [B], PARAMETRI).soggetti;
    expect(ris!.neutrali).toEqual(["d1", "d2", "d3"]);
    expect(ris!.discordi).toEqual([]);
    expect(ris!.affinita).toBe(50);
  });

  it("posizione mancante non entra nel calcolo e viene contata", () => {
    const C = soggetto("C", [2, null, null, null], cat);
    const [ris] = calcola(cat, r, [C], PARAMETRI).soggetti;
    expect(ris!.affinita).toBe(100);
    expect(ris!.mancanti).toEqual(["d2", "d3"]);
  });

  it("senza nessuna domanda confrontabile niente percentuale", () => {
    const D = soggetto("D", [null, null, null, null], cat);
    const out = calcola(cat, r, [D], PARAMETRI);
    expect(out.soggetti[0]!.affinita).toBeNull();
    expect(out.primi).toEqual([]);
    expect(out.nessunoTiRappresenta).toBe(false);
  });

  it("tutte le risposte 'non ho un'opinione' → nessun calcolo", () => {
    const A = soggetto("A", [2, 1, -2, 2], cat);
    const out = calcola(cat, risposte([0, 0, null, 0]), [A], PARAMETRI);
    expect(out.soggetti[0]!.affinita).toBeNull();
    expect(out.soggetti[0]!.risposte).toBe(0);
  });
});

describe("regressione sul mock vista-questionario.html", () => {
  // Stesse risposte usate per provare il mock nel browser: percentuali viste in pagina.
  const out = calcola(CATALOGO_MOCK, risposte([2, -2, 2, 2, -2, 2, 2, 0]), SOGGETTI_MOCK, PARAMETRI);
  const pct = Object.fromEntries(out.soggetti.map((s) => [s.id, s.affinita]));

  it("dà le stesse percentuali del mock", () => {
    expect(pct["Movimento Solidale"]).toBe(71);
    expect(pct["Verdi e Territori"]).toBe(71);
    expect(pct["Partito Lavoro e Comunità"]).toBe(64);
    expect(pct["Civica Riformista"]).toBe(61);
    expect(pct["Patto per le Regioni"]).toBe(46);
    expect(pct["Fronte dei Territori"]).toBe(39);
  });

  it("dichiara il pareggio in testa entro 3 punti", () => {
    expect(out.primi).toEqual(["Movimento Solidale", "Verdi e Territori"]);
    expect(out.nessunoTiRappresenta).toBe(false);
  });

  it("conta d'accordo e non d'accordo come il mock", () => {
    const ms = out.soggetti.find((s) => s.id === "Movimento Solidale")!;
    expect(ms.concordi.length).toBe(5);
    expect(ms.discordi.length).toBe(2);
  });

  it("segnala 'nessuno ti rappresenta' sotto il 50%", () => {
    const tuttoContro = calcola(CATALOGO_MOCK, risposte([-2, 2, -2, -2, 2, -2, -2, 2]), [SOGGETTI_MOCK[3]!], PARAMETRI);
    expect(tuttoContro.soggetti[0]!.affinita).toBeLessThan(50);
    expect(tuttoContro.nessunoTiRappresenta).toBe(true);
  });
});
