import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { calcola, type Enunciato, type Risposta, type Soggetto, type Valore } from "../src/index.js";
import { PARAMETRI, soggetto } from "./dati.js";

const N = 12;
const CAT: Enunciato[] = Array.from({ length: N }, (_, i) => ({ id: `e${String(i).padStart(2, "0")}`, tema: `t${i % 3}` }));
const valore = fc.constantFrom<Valore>(-2, -1, 0, 1, 2);
const posizioni = fc.array(fc.option(valore, { nil: null }), { minLength: N, maxLength: N });
const arbRisposte = fc
  .array(fc.record({ valore: fc.option(valore, { nil: null }), importante: fc.boolean() }), { minLength: N, maxLength: N })
  .map((rs) => Object.fromEntries(rs.map((r, i) => [CAT[i]!.id, r])) as Record<string, Risposta>);
const arbSoggetti = fc
  .array(posizioni, { minLength: 1, maxLength: 6 })
  .map((ps) => ps.map((p, i) => soggetto(`s${i}`, p, CAT)));

const nega = (v: Valore | null) => (v === null ? null : ((-v || 0) as Valore));
const negaSoggetto = (s: Soggetto): Soggetto => ({
  ...s,
  posizioni: Object.fromEntries(Object.entries(s.posizioni).map(([k, p]) => [k, { ...p, valore: nega(p.valore) }])),
});
const negaRisposte = (r: Record<string, Risposta>) =>
  Object.fromEntries(Object.entries(r).map(([k, x]) => [k, { ...x, valore: nega(x.valore) }]));
const perId = (out: ReturnType<typeof calcola>) => Object.fromEntries(out.soggetti.map((s) => [s.id, s.affinita]));

describe("proprietà", () => {
  it("simmetria: invertire tutte le risposte e tutte le posizioni non cambia nulla", () => {
    fc.assert(fc.property(arbRisposte, arbSoggetti, (r, ss) => {
      const a = calcola(CAT, r, ss, PARAMETRI);
      const b = calcola(CAT, negaRisposte(r), ss.map(negaSoggetto), PARAMETRI);
      expect(perId(b)).toEqual(perId(a));
      expect(b.primi).toEqual(a.primi);
    }));
  });

  it("l'ordine dei soggetti e del catalogo in ingresso non conta", () => {
    fc.assert(fc.property(arbRisposte, arbSoggetti, (r, ss) => {
      const a = calcola(CAT, r, ss, PARAMETRI);
      const b = calcola([...CAT].reverse(), r, [...ss].reverse(), PARAMETRI);
      expect(b.soggetti.map((s) => [s.id, s.affinita])).toEqual(a.soggetti.map((s) => [s.id, s.affinita]));
      expect(b.primi).toEqual(a.primi);
    }));
  });

  it("aggiungere un soggetto non cambia l'affinità degli altri", () => {
    fc.assert(fc.property(arbRisposte, arbSoggetti, posizioni, (r, ss, extra) => {
      const a = perId(calcola(CAT, r, ss, PARAMETRI));
      const b = perId(calcola(CAT, r, [...ss, soggetto("zz", extra, CAT)], PARAMETRI));
      delete b["zz"];
      expect(b).toEqual(a);
    }));
  });

  it("avvicinare una posizione alla risposta non riduce l'affinità", () => {
    fc.assert(fc.property(arbRisposte, posizioni, fc.nat(N - 1), (r, p, k) => {
      const e = CAT[k]!.id;
      const u = r[e]!.valore;
      const prima = p[k];
      fc.pre(u !== null && u !== 0 && prima !== null && prima !== undefined && prima !== u);
      const passo = (u! > prima! ? 1 : -1) as 1 | -1;
      const dopo = [...p];
      dopo[k] = (prima! + passo) as Valore;
      const a = calcola(CAT, r, [soggetto("s", p, CAT)], PARAMETRI).soggetti[0]!.affinita!;
      const b = calcola(CAT, r, [soggetto("s", dopo, CAT)], PARAMETRI).soggetti[0]!.affinita!;
      expect(b).toBeGreaterThanOrEqual(a);
    }));
  });

  it("limiti e conti tornano sempre", () => {
    fc.assert(fc.property(arbRisposte, arbSoggetti, (r, ss) => {
      for (const s of calcola(CAT, r, ss, PARAMETRI).soggetti) {
        if (s.affinita !== null) expect(s.affinita).toBeGreaterThanOrEqual(0);
        if (s.affinita !== null) expect(s.affinita).toBeLessThanOrEqual(100);
        expect(s.concordi.length + s.discordi.length + s.neutrali.length + s.mancanti.length).toBe(s.risposte);
        expect(s.affinita === null).toBe(s.mancanti.length === s.risposte);
      }
    }));
  });

  it("un soggetto senza posizioni non ha mai una percentuale", () => {
    fc.assert(fc.property(arbRisposte, (r) => {
      const vuoto = soggetto("v", Array(N).fill(null), CAT);
      expect(calcola(CAT, r, [vuoto], PARAMETRI).soggetti[0]!.affinita).toBeNull();
    }));
  });
});
