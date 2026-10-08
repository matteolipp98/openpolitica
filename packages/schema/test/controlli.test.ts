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
    const e = controllaRiferimenti({ ...base, "perimetro.yaml": per });
    expect(e.filter((x) => x.file === "perimetro.yaml").map((x) => x.messaggio)).toEqual(["partito sconosciuto inventato"]);
  });

  it("rifiuta un partito seguito senza programma (ADR 0020)", () => {
    const pr = structuredClone(base["programmi.yaml"]!);
    pr.elezioni[0]!.programmi = pr.elezioni[0]!.programmi.filter((p) => !p.partiti.includes("lega"));
    const e = controllaRiferimenti({ ...base, "programmi.yaml": pr });
    expect(e.map((x) => x.messaggio)).toEqual(["2022-09-25: manca il programma di lega"]);
  });

  it("rifiuta un paniere di giornali sbilanciato (ADR 0006)", () => {
    const f = structuredClone(base["fonti.yaml"]!);
    f.fonti = f.fonti.filter((x) => x.id !== "libero");
    const e = controllaRiferimenti({ ...base, "fonti.yaml": f });
    expect(e.map((x) => x.messaggio)).toEqual([
      "giornali non bilanciati per orientamento: sinistra 2, centrosinistra 2, centro 2, centrodestra 2, destra 1",
    ]);
  });

  it("rifiuta un partito seguito senza fonte (ADR 0002)", () => {
    const f = structuredClone(base["fonti.yaml"]!);
    f.fonti = f.fonti.filter((x) => x.partito !== "lega");
    const e = controllaRiferimenti({ ...base, "fonti.yaml": f });
    expect(e.map((x) => x.messaggio)).toEqual(["manca una fonte del partito lega (anche non attiva, con la nota sul perché)"]);
  });

  it("rifiuta un gruppo verificato senza identificativo", () => {
    const g = structuredClone(base["gruppi.yaml"]!);
    g.gruppi[0]!.stato = "verificato";
    g.gruppi[0]!.id_esterno = null;
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
