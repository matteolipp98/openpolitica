import { describe, expect, it } from "vitest";
import { confrontoAnni, wilson } from "../src/andamento.js";

const anno = (n: number, d: number) => Array.from({ length: 4 }, () => ({ n, d }));

describe("confrontoAnni (ADR 0040)", () => {
  it("dice 'più' solo se la differenza supera il caso", () => {
    expect(confrontoAnni([...anno(10, 50), ...anno(30, 50)], 30).verdetto).toBe("piu");
    expect(confrontoAnni([...anno(30, 50), ...anno(10, 50)], 30).verdetto).toBe("meno");
    expect(confrontoAnni([...anno(25, 50), ...anno(27, 50)], 30).verdetto).toBe("uguale");
  });
  it("con pochi dati non dice niente", () => {
    expect(confrontoAnni([...anno(1, 5), ...anno(5, 5)], 30).verdetto).toBe("pochi");
    expect(confrontoAnni(anno(10, 50), 30).verdetto).toBe("pochi");
  });
  it("somma gli ultimi quattro trimestri e i quattro prima", () => {
    const r = confrontoAnni([{ n: 99, d: 99 }, ...anno(1, 10), ...anno(2, 10)], 30);
    expect(r.prima).toEqual({ n: 4, d: 40 });
    expect(r.ora).toEqual({ n: 8, d: 40 });
  });
  it("intervallo di Wilson dentro 0–1 e attorno alla quota", () => {
    const [a, b] = wilson(5, 10);
    expect(a).toBeGreaterThan(0.18);
    expect(b).toBeLessThan(0.82);
    expect(wilson(0, 10)[0]).toBeCloseTo(0, 10);
  });
});
