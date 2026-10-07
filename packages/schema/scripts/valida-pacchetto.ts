// Valida un pacchetto dati del sito: pnpm --filter @op/schema valida-pacchetto <cartella>
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { FILE_PACCHETTO, Pacchetto } from "../src/pacchetto.js";

const cartella = path.resolve(process.argv[2] ?? "");
const FACOLTATIVI = new Set(["correzioni.json"]);
const dati = Object.fromEntries(
  FILE_PACCHETTO.filter((f) => !FACOLTATIVI.has(f) || existsSync(path.join(cartella, f))).map((f) => [
    f,
    JSON.parse(readFileSync(path.join(cartella, f), "utf8")),
  ]),
);
const r = Pacchetto.safeParse(dati);
if (!r.success) {
  for (const e of r.error.issues.slice(0, 20)) console.error(`- ${e.path.join(".")}: ${e.message}`);
  console.error(`Pacchetto non valido: ${cartella}`);
  process.exit(1);
}
const m = r.data["manifest.json"];
console.log(`Pacchetto valido: ${m.versione}${m.esempio ? " (esempio)" : ""}, ${r.data["soggetti.json"].length} soggetti, ${r.data["domande.json"].length} domande.`);
