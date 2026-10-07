// Carica il pacchetto dati al build. Senza un rilascio vero (.data/) usa l'esempio ricavato dai mock.
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { parse } from "yaml";
import type { Pacchetto, Soggetto } from "./tipi";

const VERI = path.resolve(process.cwd(), ".data");
const ESEMPIO = path.resolve(process.cwd(), "dati/esempio");
const CONTENT = path.resolve(process.cwd(), "../../content");

let cache: Pacchetto | null = null;

export function pacchetto(): Pacchetto {
  if (cache) return cache;
  const dir = existsSync(path.join(VERI, "manifest.json")) ? VERI : ESEMPIO;
  const leggi = (f: string) => JSON.parse(readFileSync(path.join(dir, f), "utf8"));
  cache = {
    manifest: leggi("manifest.json"),
    domande: leggi("domande.json"),
    soggetti: leggi("soggetti.json"),
    posizioni: leggi("posizioni.json"),
    accostamenti: leggi("accostamenti.json"),
    promesse: leggi("promesse.json"),
    andamento: leggi("andamento.json"),
  };
  return cache;
}

const alfabetico = (a: Soggetto, b: Soggetto) => a.nome.localeCompare(b.nome, "it"); // ADR 0009

export const partiti = () => pacchetto().soggetti.filter((s) => s.tipo === "partito").sort(alfabetico);
export const persone = () => pacchetto().soggetti.filter((s) => s.tipo === "persona").sort(alfabetico);

/** Regole e soglie metodologiche: sempre quelle vere di content/, anche con i dati di esempio. */
export function contenuto<T = unknown>(file: string): T {
  return parse(readFileSync(path.join(CONTENT, file), "utf8")) as T;
}

export interface Parametri {
  presentazione: { denominatoreMinimo: number };
  affinita: { pesoImportante: number; margineParita: number; sogliaNessunoTiRappresenta: number };
}
export const parametri = () => contenuto<Parametri>("parametri.yaml");
