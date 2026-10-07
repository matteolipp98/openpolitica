// Controllo del linguaggio (ADR 0036, #28): nessuna parola vietata nelle frasi che legge chi visita il sito.
// Guarda le stringhe con almeno uno spazio e il testo tra i tag, nei componenti del sito e nei mock.
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { parse } from "yaml";

const RADICE = path.resolve(import.meta.dirname, "../../..");
const { vietate } = parse(readFileSync(path.join(RADICE, "content/parole.yaml"), "utf8")) as {
  vietate: { parola: string; usa: string }[];
};
const CARTELLE = ["apps/web/app", "apps/web/components", "apps/web/lib", "adr/mockup"];

function file(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = path.join(dir, n);
    return statSync(p).isDirectory() ? file(p) : /\.(tsx?|html)$/.test(n) ? [p] : [];
  });
}

/** Frasi visibili: stringhe con uno spazio e testo tra tag; senza commenti. */
export function frasi(sorgente: string): string[] {
  const senzaCommenti = sorgente
    .replace(/<!--[\s\S]*?-->/g, " ")
    .replace(/\/\*[\s\S]*?\*\//g, " ")
    .replace(/(^|\s)\/\/\s.*$/gm, " ")
    .replace(/{\/\*[\s\S]*?\*\/}/g, " ");
  const out: string[] = [];
  for (const m of senzaCommenti.matchAll(/"([^"\n]*\s[^"\n]*)"|'([^'\n]*\s[^'\n]*)'|`([^`]*\s[^`]*)`/g)) out.push(m[1] ?? m[2] ?? m[3]!);
  for (const m of senzaCommenti.matchAll(/(?:<[a-z][\w-]*(?:\s[^<>]*)?>|<\/[a-z][\w-]*>)([^<>{}]*[a-zàèéìòù][^<>{}]*)</gi)) out.push(m[1]!);
  return out;
}

export function violazioni(testo: string): { parola: string; usa: string }[] {
  return vietate.filter((v) => new RegExp(`(^|[^\\p{L}])${v.parola}`, "iu").test(testo));
}

const errori: string[] = [];
for (const c of CARTELLE)
  for (const f of file(path.join(RADICE, c)))
    for (const frase of frasi(readFileSync(f, "utf8")))
      for (const v of violazioni(frase))
        errori.push(`${path.relative(RADICE, f)}: «${frase.trim().slice(0, 90)}» → al posto di "${v.parola}" usa: ${v.usa}`);

if (errori.length) {
  console.error(errori.join("\n"));
  console.error(`\n${errori.length} frasi con parole da non usare (ADR 0036, content/parole.yaml).`);
  process.exit(1);
}
console.log("Linguaggio: nessuna parola da non usare.");
