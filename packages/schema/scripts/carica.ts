import { readFileSync, readdirSync, existsSync } from "node:fs";
import path from "node:path";
import { parse } from "yaml";
import { z } from "zod";
import { Alias, SCHEMI } from "../src/content.js";

export const CONTENT = path.resolve(import.meta.dirname, "../../../content");

type Contenuti = { [K in keyof typeof SCHEMI]: z.infer<(typeof SCHEMI)[K]> } & {
  alias: Record<string, z.infer<typeof Alias>>;
};

export interface Errore { file: string; messaggio: string }

function leggi(file: string): unknown {
  return parse(readFileSync(path.join(CONTENT, file), "utf8"));
}

function formatta(e: z.ZodError): string[] {
  return e.issues.map((i) => `${i.path.join(".") || "(radice)"}: ${i.message}`);
}

/** Carica e valida ogni file; raccoglie tutti gli errori invece di fermarsi al primo. */
export function caricaContenuti(): { contenuti: Partial<Contenuti>; errori: Errore[] } {
  const errori: Errore[] = [];
  const contenuti: Partial<Contenuti> = {};
  for (const [file, schema] of Object.entries(SCHEMI)) {
    if (!existsSync(path.join(CONTENT, file))) { errori.push({ file, messaggio: "file mancante" }); continue; }
    const r = schema.safeParse(leggi(file));
    if (r.success) (contenuti as Record<string, unknown>)[file] = r.data;
    else for (const m of formatta(r.error)) errori.push({ file, messaggio: m });
  }
  contenuti.alias = {};
  for (const f of readdirSync(path.join(CONTENT, "alias")).filter((f) => f.endsWith(".yaml"))) {
    const file = `alias/${f}`;
    const r = Alias.safeParse(leggi(file));
    if (!r.success) { for (const m of formatta(r.error)) errori.push({ file, messaggio: m }); continue; }
    if (`${r.data.slug}.yaml` !== f) errori.push({ file, messaggio: `il nome del file deve essere ${r.data.slug}.yaml` });
    contenuti.alias[r.data.slug] = r.data;
  }
  return { contenuti, errori };
}
