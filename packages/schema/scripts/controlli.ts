// Controlli incrociati tra i file di content/ (riferimenti, duplicati, regole degli ADR).
import { ORIENTAMENTI } from "../src/content.js";
import type { Errore } from "./carica.js";
import type { caricaContenuti } from "./carica.js";

type C = ReturnType<typeof caricaContenuti>["contenuti"];

export function controllaRiferimenti(c: C): Errore[] {
  const e: Errore[] = [];
  const err = (file: string, messaggio: string) => e.push({ file, messaggio });
  const partiti = new Set(c["partiti.yaml"]?.partiti.map((p) => p.slug) ?? []);
  const coalizioni = new Set(c["partiti.yaml"]?.coalizioni.map((x) => x.slug) ?? []);

  const dup = (lista: string[], file: string, cosa: string) => {
    const visti = new Set<string>();
    for (const x of lista) { if (visti.has(x)) err(file, `${cosa} duplicato: ${x}`); visti.add(x); }
  };
  dup(c["temi.yaml"]?.temi.map((t) => t.id) ?? [], "temi.yaml", "tema");
  dup([...partiti], "partiti.yaml", "partito");
  dup(c["partiti.yaml"]?.partiti.map((p) => p.slug) ?? [], "partiti.yaml", "partito");

  for (const p of c["partiti.yaml"]?.partiti ?? [])
    for (const k of p.coalizioni) if (!coalizioni.has(k.coalizione)) err("partiti.yaml", `${p.slug}: coalizione sconosciuta ${k.coalizione}`);

  for (const g of c["gruppi.yaml"]?.gruppi ?? []) {
    for (const p of g.partiti) if (!partiti.has(p)) err("gruppi.yaml", `gruppo "${g.nome_contiene}": partito sconosciuto ${p}`);
    if (g.stato === "verificato" && !g.id_esterno) err("gruppi.yaml", `gruppo "${g.nome_contiene}" verificato senza id_esterno`);
  }

  const per = c["perimetro.yaml"];
  if (per) {
    for (const p of per.partiti) if (!partiti.has(p.slug)) err("perimetro.yaml", `partito sconosciuto ${p.slug}`);
    for (const p of per.persone) {
      if (!partiti.has(p.partito)) err("perimetro.yaml", `${p.slug}: partito sconosciuto ${p.partito}`);
      if (!c.alias?.[p.slug]) err("perimetro.yaml", `${p.slug}: manca content/alias/${p.slug}.yaml`);
    }
    if (c["parametri.yaml"] && per.legislatura !== c["parametri.yaml"].posizioni.legislaturaRiferimento)
      err("perimetro.yaml", "legislatura diversa da parametri.posizioni.legislaturaRiferimento");
  }

  // ADR 0020: ogni partito seguito ha il suo programma per ogni elezione elencata
  for (const el of c["programmi.yaml"]?.elezioni ?? []) {
    const coperti = el.programmi.flatMap((p) => p.partiti);
    dup(coperti, "programmi.yaml", `partito nel ${el.data}`);
    for (const p of coperti) if (!partiti.has(p)) err("programmi.yaml", `${el.data}: partito sconosciuto ${p}`);
    for (const p of per?.partiti ?? [])
      if (!coperti.includes(p.slug)) err("programmi.yaml", `${el.data}: manca il programma di ${p.slug}`);
  }

  // ADR 0002, 0006: fonti con riferimenti validi e paniere dei giornali bilanciato
  const fonti = c["fonti.yaml"]?.fonti ?? [];
  dup(fonti.map((f) => f.id), "fonti.yaml", "fonte");
  dup(fonti.map((f) => f.url), "fonti.yaml", "indirizzo");
  const persone = new Set(per?.persone.map((p) => p.slug) ?? []);
  for (const f of fonti) {
    if (f.partito && !partiti.has(f.partito)) err("fonti.yaml", `${f.id}: partito sconosciuto ${f.partito}`);
    if (f.persona && !persone.has(f.persona)) err("fonti.yaml", `${f.id}: persona fuori dal perimetro ${f.persona}`);
    if (f.link) try { new RegExp(f.link); } catch { err("fonti.yaml", `${f.id}: espressione regolare non valida`); }
  }
  for (const p of per?.partiti ?? [])
    if (fonti.length && !fonti.some((f) => f.partito === p.slug))
      err("fonti.yaml", `manca una fonte del partito ${p.slug} (anche non attiva, con la nota sul perché)`);
  const perOrientamento = new Map<string, number>();
  for (const f of fonti)
    if (f.tipo === "testata" && f.attiva) perOrientamento.set(f.orientamento!, (perOrientamento.get(f.orientamento!) ?? 0) + 1);
  if (new Set(perOrientamento.values()).size > 1)
    err("fonti.yaml", `giornali non bilanciati per orientamento: ${[...perOrientamento].map(([o, n]) => `${o} ${n}`).join(", ")}`);
  if (fonti.length && perOrientamento.size !== ORIENTAMENTI.length)
    err("fonti.yaml", `servono giornali di ogni orientamento (${ORIENTAMENTI.join(", ")})`);

  // ADR 0027: una forma nominale non può appartenere a due persone
  const forme = new Map<string, string>();
  for (const a of Object.values(c.alias ?? {}))
    for (const f of a.forme) {
      const k = f.toLocaleLowerCase("it");
      const altro = forme.get(k);
      if (altro && altro !== a.slug) err(`alias/${a.slug}.yaml`, `forma "${f}" usata anche da ${altro}`);
      forme.set(k, a.slug);
    }
  for (const a of Object.values(c.alias ?? {}))
    for (const ca of a.cariche) if (ca.partito && !partiti.has(ca.partito)) err(`alias/${a.slug}.yaml`, `partito sconosciuto ${ca.partito}`);

  return e;
}

/** Fatti non ancora confermati: non bloccano, ma vanno elencati (ADR 0027: mai inventare). */
export function elencoDaVerificare(c: C): string[] {
  const out: string[] = [];
  for (const p of c["partiti.yaml"]?.partiti ?? []) for (const r of p.ruolo) if (r.da_verificare) out.push(`partiti.yaml: ruolo di ${p.slug}`);
  for (const g of c["gruppi.yaml"]?.gruppi ?? []) if (g.stato === "da_verificare") out.push(`gruppi.yaml: ${g.ramo} "${g.nome_contiene}"`);
  for (const a of Object.values(c.alias ?? {})) {
    for (const ca of a.cariche) if (ca.da_verificare || !ca.valido_dal) out.push(`alias/${a.slug}.yaml: data della carica "${ca.carica}"`);
    if (a.ids_esterni.length === 0) out.push(`alias/${a.slug}.yaml: identificativi Camera/Senato`);
  }
  return out;
}
