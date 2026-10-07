// Test di equilibrio su un pacchetto di dati del sito (piano §3.11):
//   pnpm --filter @op/affinita equilibrio <cartella del pacchetto>
// Esce con errore se il catalogo premia uno schieramento. Senza domande non c'è niente da controllare.
import { readFileSync } from "node:fs";
import path from "node:path";
import { parse } from "yaml";
import { equilibrio, type Soggetto } from "../src/index.js";

const cartella = path.resolve(process.argv[2] ?? "");
const leggi = (f: string) => JSON.parse(readFileSync(path.join(cartella, f), "utf8"));
const parametri = parse(readFileSync(new URL("../../../content/parametri.yaml", import.meta.url), "utf8"));

const domande: { id: string; tema: string }[] = leggi("domande.json");
if (domande.length === 0) {
  console.log("Nessuna domanda nel pacchetto: test di equilibrio non necessario.");
  process.exit(0);
}
const posizioni: Record<string, Record<string, { valore: -2 | -1 | 0 | 1 | 2 | null; stato: Soggetto["posizioni"][string]["stato"] }>> =
  leggi("posizioni.json");
const partiti = (leggi("soggetti.json") as { id: string; nome: string; tipo: string; ruolo: string }[]).filter((s) => s.tipo === "partito");
const soggetti: Soggetto[] = partiti.map((p) => ({
  id: p.id,
  nome: p.nome,
  tipo: "partito",
  posizioni: Object.fromEntries(
    Object.entries(posizioni[p.id] ?? {}).map(([k, v]) => [k, { valore: v.valore, stato: v.stato, confidenza: v.valore === null ? null : "piena" }]),
  ),
}));
const aree = Object.fromEntries(
  partiti.map((p) => [p.id, /opposizione/i.test(p.ruolo) ? "opposizione" : /governo/i.test(p.ruolo) ? "governo" : "altro"]),
);
const r = equilibrio(domande, soggetti, aree, parametri.affinita, parametri.equilibrio);

console.log(`Test di equilibrio: ${domande.length} domande, ${soggetti.length} partiti, ${r.n} questionari simulati.`);
console.log(`Primi posti per area (risposte a caso): ${JSON.stringify(r.quotaPrimiPerArea)}; quota di partiti: ${JSON.stringify(r.quotaSoggettiPerArea)}`);
console.log(`Riconoscimento delle aree: ${JSON.stringify(r.riconoscimentoArea)}`);
if (r.problemi.length) {
  console.error("Test di equilibrio NON superato:");
  for (const p of r.problemi) console.error(`- ${p}`);
  process.exit(1);
}
console.log("Test di equilibrio superato.");
