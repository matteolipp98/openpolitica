import { describe, expect, it } from "vitest";
import { equilibrio, type Soglie } from "../src/index.js";
import { CATALOGO_MOCK, PARAMETRI, SOGGETTI_MOCK, soggetto } from "./dati.js";

const SOGLIE: Soglie = { scartoAffinitaMedia: 5, scartoQuotaPrimi: 10, riconoscimentoArea: 0.7 };
const CAT = Array.from({ length: 10 }, (_, i) => ({ id: `e${i}`, tema: "t" }));

describe("equilibrio (piano §3.11)", () => {
  it("catalogo che distingue due aree simmetriche: superato", () => {
    const a = soggetto("a", CAT.map((_, i) => (i % 2 ? 2 : -2)), CAT);
    const b = soggetto("b", CAT.map((_, i) => (i % 2 ? -2 : 2)), CAT);
    const r = equilibrio(CAT, [a, b], { a: "governo", b: "opposizione" }, PARAMETRI, SOGLIE, 2000);
    expect(r.problemi).toEqual([]);
    expect(Math.abs(r.affinitaMedia.a! - 50)).toBeLessThan(2);
    expect(r.riconoscimentoArea.governo).toBeGreaterThan(0.9);
  });

  it("aree con le stesse posizioni: le domande non le distinguono, il test fallisce", () => {
    const a = soggetto("a", CAT.map(() => 2), CAT);
    const b = soggetto("b", CAT.map(() => 2), CAT);
    const r = equilibrio(CAT, [a, b], { a: "governo", b: "opposizione" }, PARAMETRI, SOGLIE, 2000);
    expect(r.problemi.some((p) => p.includes("non distinguono"))).toBe(true);
  });

  it("stesso seme, stesso rapporto", () => {
    const aree = Object.fromEntries(SOGGETTI_MOCK.map((s, i) => [s.id, i % 2 ? "governo" : "opposizione"]));
    const x = equilibrio(CATALOGO_MOCK, SOGGETTI_MOCK, aree, PARAMETRI, SOGLIE, 500);
    const y = equilibrio(CATALOGO_MOCK, SOGGETTI_MOCK, aree, PARAMETRI, SOGLIE, 500);
    expect(x).toEqual(y);
  });
});
