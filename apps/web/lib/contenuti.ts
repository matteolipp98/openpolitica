// Dati del sito letti al momento del build. Fase 0: anagrafica da content/; voti e domande
// arriveranno dal bundle di rilascio (piano §3.9). Nessuna lettura del database a runtime.
import { readFileSync } from "node:fs";
import path from "node:path";
import { parse } from "yaml";
import { Alias, Partiti, Perimetro } from "@op/schema";

const CONTENT = path.resolve(process.cwd(), "../../content");
const leggi = (f: string) => parse(readFileSync(path.join(CONTENT, f), "utf8"));

export interface SoggettoPagina {
  slug: string;
  nome: string;
  ruolo: string; // es. "Al governo" o "Fratelli d'Italia · Presidente del Consiglio dei ministri"
  tipo: "partito" | "persona";
  partito?: string;
}

const ordine = (a: SoggettoPagina, b: SoggettoPagina) => a.nome.localeCompare(b.nome, "it"); // ADR 0009

export function partiti(): SoggettoPagina[] {
  const anag = Partiti.parse(leggi("partiti.yaml"));
  const per = Perimetro.parse(leggi("perimetro.yaml"));
  const seguiti = new Set(per.partiti.map((p) => p.slug));
  return anag.partiti
    .filter((p) => seguiti.has(p.slug))
    .map((p) => {
      const attuale = p.ruolo.find((r) => r.valido_al === null) ?? p.ruolo.at(-1)!;
      return {
        slug: p.slug,
        nome: p.nome,
        tipo: "partito" as const,
        ruolo: attuale.valore === "governo" ? "Al governo" : "All'opposizione",
      };
    })
    .sort(ordine);
}

export function persone(): SoggettoPagina[] {
  const per = Perimetro.parse(leggi("perimetro.yaml"));
  const nomiPartiti = new Map(partiti().map((p) => [p.slug, p.nome]));
  return per.persone
    .map((pp) => {
      const a = Alias.parse(leggi(`alias/${pp.slug}.yaml`));
      const carica = a.cariche[0]?.carica ?? "";
      return {
        slug: a.slug,
        nome: `${a.nome} ${a.cognome}`,
        tipo: "persona" as const,
        partito: pp.partito,
        ruolo: [nomiPartiti.get(pp.partito), carica.charAt(0).toLowerCase() + carica.slice(1)].filter(Boolean).join(" · "),
      };
    })
    .sort(ordine);
}
