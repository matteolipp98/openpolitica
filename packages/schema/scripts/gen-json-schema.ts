// Genera content/schema/*.json dagli schemi zod. In CI si verifica che siano allineati (git diff).
import { writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { zodToJsonSchema } from "zod-to-json-schema";
import { Alias, SCHEMI } from "../src/content.js";
import { CONTENT } from "./carica.js";

const out = path.join(CONTENT, "schema");
mkdirSync(out, { recursive: true });
const tutti = { ...SCHEMI, "alias.yaml": Alias };
for (const [file, schema] of Object.entries(tutti)) {
  const nome = file.replace(/\.yaml$/, ".schema.json");
  writeFileSync(path.join(out, nome), JSON.stringify(zodToJsonSchema(schema, { $refStrategy: "none" }), null, 2) + "\n");
}
console.log(`Scritti ${Object.keys(tutti).length} schemi in content/schema/`);
