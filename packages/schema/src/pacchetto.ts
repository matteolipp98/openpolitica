// Schema del pacchetto dati che il sito legge al build (piano §3.9). Lo stesso per i dati di esempio
// e per i rilasci veri: un pacchetto che non lo rispetta non arriva mai in produzione.
import { z } from "zod";

const Conteggio = z.object({ n: z.number().int().min(0), d: z.number().int().min(0) }).refine((c) => c.n <= c.d, "n > d");
const slug = z.string().regex(/^[a-z0-9]+(-[a-z0-9]+)*$/);
const giorno = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
const TEMA_PROMESSA = z.enum(["economia", "welfare", "diritti", "ambiente", "istituzioni", "esteri", "altro"]);

/** L'ultimo programma elettorale del partito, letto da noi (home, ADR 0036). */
export const PProgramma = z.object({
  elezione: giorno,
  promesse: z.number().int().min(0),
  /** Promesse che dicono quanto e entro quando (regola fissa, pagina del metodo). */
  precise: Conteggio,
  /** Promesse per tema; assente finché i temi non sono assegnati (#75). */
  temi: z.record(TEMA_PROMESSA, z.number().int().min(0)).optional(),
  /** Altri partiti con lo stesso programma: stesso file, oppure testo in gran parte uguale. */
  comune: z.object({ stesso_documento: z.array(slug), testo_uguale: z.array(slug) }).optional(),
}).refine((p) => p.precise.d === p.promesse, "precise.d diverso dal numero di promesse")
  .refine((p) => !p.temi || Object.values(p.temi).reduce((a, b) => a + b, 0) <= p.promesse, "più promesse per tema che in tutto");

export const PManifest = z.object({
  versione: z.string().min(1),
  esempio: z.boolean(),
  generato_il: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  catalogo: z.object({ versione: z.string(), stato: z.enum(["provvisorio", "definitivo"]) }),
  sezioni: z.object({ posizioni: z.boolean(), numeri: z.boolean(), coerenza: z.boolean(), promesse: z.boolean(), letture: z.boolean() }),
}).passthrough();

export const PSoggetto = z.object({
  id: slug,
  slug,
  tipo: z.enum(["partito", "persona"]),
  nome: z.string().min(2),
  ruolo: z.string(),
  partito: slug.optional(),
  numeri: z.object({ sbagliati: z.number().int().min(0), controllati: z.number().int().min(0) }).optional(),
  vaghi: Conteggio.optional(),
  coerenza: z.object({ contrari: z.number().int().min(0), confrontabili: z.number().int().min(0) }).optional(),
  promesse: z.object({ mantenute: z.number().int().min(0), totali: z.number().int().min(0) }).optional(),
  indicatori: z.object({ precise: Conteggio, soldi: Conteggio, inTempo: Conteggio, attacchi: Conteggio }).optional(),
  /** Per i partiti: le persone che seguiamo perché lo guidano. */
  guida: z.array(z.object({ nome: z.string().min(2), slug: slug.optional() })).optional(),
  programma: PProgramma.optional(),
});

export const PDomanda = z.object({
  id: z.string(),
  testo: z.string().min(5),
  tema: z.string(),
  contesto: z.object({ fatto: z.string(), favorevoli: z.string(), contrari: z.string() }),
  /** Giorno e ramo del voto da cui viene la domanda. */
  data: giorno.optional(),
  ramo: z.enum(["camera", "senato"]).optional(),
});

/** Il Parlamento alla data del pacchetto: seggi per partito seguito, il resto negli "altri". */
export const PParlamento = z.object({
  data: giorno,
  rami: z.record(z.enum(["camera", "senato"]), z.object({
    totale: z.number().int().positive(),
    partiti: z.record(slug, z.number().int().min(0)),
    altri: z.number().int().min(0),
  }).refine((r) => Object.values(r.partiti).reduce((a, b) => a + b, 0) + r.altri === r.totale, "i seggi non tornano con il totale")),
});

export const PPosizione = z.object({
  valore: z.union([z.literal(-2), z.literal(-1), z.literal(0), z.literal(1), z.literal(2), z.null()]),
  stato: z.enum(["documentata", "non_documentata", "divergente"]),
  evidenze: z.array(z.object({ testo: z.string(), quando: z.string(), url: z.string().url().optional() })),
  nota: z.string().optional(),
}).refine((p) => (p.valore === null) === (p.stato === "non_documentata"), "valore e stato non coerenti");

const MetricaTempo = z.enum(["vota_con_governo", "vota_compatto", "numeri_sbagliati", "promesse_precise", "annunci_seguiti", "frasi_contro"]);

export const PAndamento = z.object({
  trimestri: z.array(z.string().regex(/^\d{4}-T[1-4]$/)),
  governo: z.record(z.array(z.boolean())),
  serie: z.record(z.record(MetricaTempo, z.array(Conteggio))),
}).passthrough().superRefine((a, ctx) => {
  for (const [s, m] of Object.entries(a.serie))
    for (const [k, v] of Object.entries(m))
      if (v.length !== a.trimestri.length) ctx.addIssue({ code: "custom", message: `${s}.${k}: ${v.length} punti, ${a.trimestri.length} trimestri` });
});

export const Pacchetto = z.object({
  "manifest.json": PManifest,
  "domande.json": z.array(PDomanda),
  "soggetti.json": z.array(PSoggetto).min(1),
  "posizioni.json": z.record(z.record(PPosizione)),
  "accostamenti.json": z.record(z.array(z.object({
    detto: z.string(), dove: z.string(), vero: z.string(), fonte: z.string(),
    esito: z.enum(["sbagliato", "quasi"]).nullable(), frase: z.string(),
  }))),
  "promesse.json": z.record(z.array(z.object({
    stato: z.enum(["mantenuta", "a_meta", "non_mantenuta"]), testo: z.string(), motivo: z.string(),
  }))),
  "andamento.json": PAndamento,
  // Facoltativo: i pacchetti pubblicati prima del 7 ottobre 2026 non lo hanno
  "correzioni.json": z.array(z.object({
    quando: z.string().regex(/^\d{4}-\d{2}-\d{2}$/), oggetto: z.string(), prima: z.string(), dopo: z.string(), motivo: z.string().min(3),
  })).optional(),
  // Facoltativo: i pacchetti pubblicati prima dell'8 ottobre 2026 non lo hanno
  "parlamento.json": PParlamento.optional(),
}).superRefine((p, ctx) => {
  const ids = new Set(p["soggetti.json"].map((s) => s.id));
  if (ids.size !== p["soggetti.json"].length) ctx.addIssue({ code: "custom", message: "soggetti ripetuti" });
  if (p["manifest.json"].sezioni.posizioni && p["domande.json"].length === 0)
    ctx.addIssue({ code: "custom", message: "sezioni.posizioni è vero ma non ci sono domande" });
  for (const s of p["soggetti.json"])
    if (s.partito && !ids.has(s.partito)) ctx.addIssue({ code: "custom", message: `${s.id}: partito sconosciuto ${s.partito}` });
  for (const s of p["soggetti.json"])
    for (const g of s.guida ?? [])
      if (g.slug && !ids.has(g.slug)) ctx.addIssue({ code: "custom", message: `${s.id}: guida sconosciuta ${g.slug}` });
  for (const s of p["soggetti.json"])
    for (const c of [...(s.programma?.comune?.stesso_documento ?? []), ...(s.programma?.comune?.testo_uguale ?? [])])
      if (!ids.has(c)) ctx.addIssue({ code: "custom", message: `${s.id}: programma comune con un partito sconosciuto ${c}` });
  for (const r of Object.values(p["parlamento.json"]?.rami ?? {}))
    for (const s of Object.keys(r.partiti))
      if (!ids.has(s)) ctx.addIssue({ code: "custom", message: `seggi di un partito sconosciuto: ${s}` });
  for (const s of Object.keys(p["posizioni.json"]))
    if (!ids.has(s)) ctx.addIssue({ code: "custom", message: `posizioni di un soggetto sconosciuto: ${s}` });
});

export const FILE_PACCHETTO = Object.keys(Pacchetto._def.schema.shape) as (keyof z.infer<typeof Pacchetto>)[];
