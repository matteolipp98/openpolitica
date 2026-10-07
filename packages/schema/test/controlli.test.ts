import { describe, expect, it } from "vitest";
import { caricaContenuti } from "../scripts/carica.js";
import { controllaRiferimenti } from "../scripts/controlli.js";
import { Letture, Scala } from "../src/content.js";

describe("contenuti del repository", () => {
  it("sono validi e coerenti", () => {
    const { contenuti, errori } = caricaContenuti();
    expect(errori).toEqual([]);
    expect(controllaRiferimenti(contenuti)).toEqual([]);
  });
});

describe("controlli incrociati", () => {
  const base = caricaContenuti().contenuti;

  it("rifiuta una forma nominale usata da due persone (ADR 0027)", () => {
    const alias = structuredClone(base.alias!);
    alias["matteo-renzi"]!.forme.push("Matteo Salvini");
    const e = controllaRiferimenti({ ...base, alias });
    expect(e.some((x) => x.messaggio.includes("Matteo Salvini"))).toBe(true);
  });

  it("rifiuta un partito sconosciuto nel perimetro", () => {
    const per = structuredClone(base["perimetro.yaml"]!);
    per.partiti.push({ slug: "inventato", motivo: "x" });
    expect(controllaRiferimenti({ ...base, "perimetro.yaml": per }).length).toBe(1);
  });

  it("rifiuta un gruppo verificato senza identificativo", () => {
    const g = structuredClone(base["gruppi.yaml"]!);
    g.gruppi[0]!.stato = "verificato";
    expect(controllaRiferimenti({ ...base, "gruppi.yaml": g }).length).toBe(1);
  });
});

describe("schemi", () => {
  it("la scala ha cinque livelli distinti", () => {
    const livelli = [2, 1, 0, -1, -1].map((valore) => ({ valore, etichetta: "x", descrizione: "x" }));
    expect(Scala.safeParse({ versione: 1, livelli }).success).toBe(false);
  });
  it("le frasi per soggetto finiscono con 'altrimenti'", () => {
    const r = Letture.safeParse({ versione: 1, letture: [], frasiNumeri: [{ se: "a", testo: "x" }, { se: "b", testo: "y" }] });
    expect(r.success).toBe(false);
  });
});
