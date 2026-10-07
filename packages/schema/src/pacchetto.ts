// Schema del pacchetto dati che il sito legge al build (piano §3.9). Lo stesso per i dati di esempio
// e per i rilasci veri: un pacchetto che non lo rispetta non arriva mai in produzione.
import { z } from "zod";

const Conteggio = z.object({ n: z.number().int().min(0), d: z.number().int().min(0) }).refine((c) => c.n <= c.d, "n > d");
const slug = z.string().regex(/^[a-z0-9]+(-[a-z0-9]+)*$/);

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
});

export const PDomanda = z.object({
  id: z.string(),
  testo: z.string().min(5),
  tema: z.string(),
  contesto: z.object({ fatto: z.string(), favorevoli: z.string(), contrari: z.string() }),
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
}).superRefine((p, ctx) => {
  const ids = new Set(p["soggetti.json"].map((s) => s.id));
  if (ids.size !== p["soggetti.json"].length) ctx.addIssue({ code: "custom", message: "soggetti ripetuti" });
  if (p["manifest.json"].sezioni.posizioni && p["domande.json"].length === 0)
    ctx.addIssue({ code: "custom", message: "sezioni.posizioni è vero ma non ci sono domande" });
  for (const s of p["soggetti.json"])
    if (s.partito && !ids.has(s.partito)) ctx.addIssue({ code: "custom", message: `${s.id}: partito sconosciuto ${s.partito}` });
  for (const s of Object.keys(p["posizioni.json"]))
    if (!ids.has(s)) ctx.addIssue({ code: "custom", message: `posizioni di un soggetto sconosciuto: ${s}` });
});

export const FILE_PACCHETTO = Object.keys(Pacchetto._def.schema.shape) as (keyof z.infer<typeof Pacchetto>)[];
