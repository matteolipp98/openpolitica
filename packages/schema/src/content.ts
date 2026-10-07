// Schemi del contenuto metodologico in content/ (ADR 0025).
// Da qui si generano i JSON Schema in content/schema/, usati anche dai worker Python.
import { z } from "zod";

const slug = z.string().regex(/^[a-z0-9]+(-[a-z0-9]+)*$/, "solo minuscole, cifre e trattini");
const data = z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "data nel formato AAAA-MM-GG");
const url = z.string().url();

/** Un fatto che non abbiamo ancora potuto confermare su una fonte: si dichiara, non si inventa. */
const daVerificare = z.boolean().default(false);

export const Valore = z.union([z.literal(-2), z.literal(-1), z.literal(0), z.literal(1), z.literal(2)]);
export type Valore = z.infer<typeof Valore>;

// ---------- Temi (ADR 0022, 0035) ----------
export const Tema = z.object({
  id: slug,
  nome: z.string().min(3).max(40),
  descrizione: z.string().min(10).max(140),
  esempi: z.array(z.string()).min(1).max(6),
});
export const Temi = z.object({
  versione: z.number().int().positive(),
  stato: z.enum(["proposta", "approvata"]),
  temi: z.array(Tema).min(2).max(19),
});

// ---------- Scala delle posizioni (ADR 0035) ----------
export const Scala = z.object({
  versione: z.number().int().positive(),
  livelli: z
    .array(z.object({ valore: Valore, etichetta: z.string(), descrizione: z.string() }))
    .length(5)
    .refine((l) => new Set(l.map((x) => x.valore)).size === 5, "valori ripetuti"),
});

// ---------- Parametri (ADR 0019, 0023, 0030, 0037) ----------
export const Parametri = z.object({
  versione: z.number().int().positive(),
  presentazione: z.object({ denominatoreMinimo: z.number().int().positive() }),
  affinita: z.object({
    pesoImportante: z.number().int().min(1),
    margineParita: z.number().int().min(0),
    sogliaNessunoTiRappresenta: z.number().int().min(0).max(100),
  }),
  posizioni: z.object({
    quotaMaggioranzaGruppo: z.number().gt(0).lt(1),
    membriMinimi: z.number().int().positive(),
    legislaturaRiferimento: z.number().int().positive(),
  }),
  catalogo: z.object({
    enunciatiPerTema: z.number().int().positive(),
    minoranzaMinima: z.number().gt(0).lt(0.5),
  }),
  equilibrio: z.object({
    scartoAffinitaMedia: z.number().positive(),
    scartoQuotaPrimi: z.number().positive(),
    riconoscimentoArea: z.number().gt(0).lt(1),
  }),
});

// ---------- Letture e frasi (ADR 0037) ----------
export const Metrica = z.enum(["numeri_sbagliati", "non_controllabili", "voti_contrari", "promesse_non_mantenute"]);
export const Letture = z.object({
  versione: z.number().int().positive(),
  frasiNumeri: z
    .array(z.object({ se: z.string().optional(), altrimenti: z.literal(true).optional(), testo: z.string().max(120) }))
    .min(2)
    .refine((f) => f.at(-1)?.altrimenti === true, "l'ultima frase deve essere 'altrimenti'"),
  letture: z.array(
    z.object({
      metrica: Metrica,
      verso: z.enum(["max", "min"]).optional(),
      aggregata: z.boolean().default(false),
      testo: z.string().max(120),
      testoPiu: z.string().max(120).optional(), // per i pareggi: si nominano tutti (ADR 0037)
      sotto: z.string().max(120),
    }),
  ),
});

// ---------- Governance (ADR 0021, 0028, 0037) ----------
export const Governance = z.object({
  versione: z.number().int().positive(),
  revisioneUmana: z.object({ attiva: z.boolean(), revisori: z.number().int().min(0) }),
  campagna: z.object({ attiva: z.boolean(), dal: data.nullable() }),
});

// ---------- Partiti e coalizioni (ADR 0027, 0021) ----------
const Periodo = z.object({ valido_dal: data.nullable(), valido_al: data.nullable().default(null), da_verificare: daVerificare });

export const Partito = z.object({
  slug,
  nome: z.string(),
  nomi_alternativi: z.array(z.string()).default([]),
  sito: url.optional(),
  ruolo: z.array(Periodo.extend({ valore: z.enum(["governo", "opposizione"]) })).min(1),
  coalizioni: z.array(z.object({ elezione: data, coalizione: slug })).default([]),
  note: z.string().optional(),
});
export const Coalizione = z.object({ slug, nome: z.string(), elezione: data });
export const Partiti = z.object({
  versione: z.number().int().positive(),
  aggiornato_il: data,
  partiti: z.array(Partito),
  coalizioni: z.array(Coalizione),
});

// ---------- Gruppi parlamentari -> partiti ----------
export const Gruppo = z.object({
  ramo: z.enum(["camera", "senato"]),
  legislatura: z.number().int(),
  nome_contiene: z.string().min(3),
  id_esterno: z.string().nullable(),
  sigla: z.string().nullable(),
  partiti: z.array(slug), // vuoto = gruppo misto: si attribuisce per persona
  periodo: Periodo,
  stato: z.enum(["da_verificare", "verificato"]),
});
export const Gruppi = z.object({ versione: z.number().int().positive(), gruppi: z.array(Gruppo) });

// ---------- Perimetro (ADR 0002) ----------
export const Perimetro = z.object({
  versione: z.number().int().positive(),
  aggiornato_il: data,
  legislatura: z.number().int(),
  criterio: z.string().min(40),
  partiti: z.array(z.object({ slug, motivo: z.string() })),
  persone: z.array(z.object({ slug, partito: slug, motivo: z.string() })),
});

// ---------- Alias e identità (ADR 0027) ----------
export const Alias = z.object({
  slug,
  nome: z.string(),
  cognome: z.string(),
  forme: z.array(z.string().min(5)).min(1),
  forme_escluse: z.array(z.object({ forma: z.string(), motivo: z.string() })).default([]),
  cariche: z.array(Periodo.extend({ carica: z.string(), partito: slug.optional(), fonte: url.optional() })).min(1),
  ids_esterni: z
    .array(Periodo.extend({ fonte: z.enum(["camera", "senato", "openpolis"]), id: z.string() }))
    .default([]),
});

// ---------- Catalogo delle domande (ADR 0022, 0030, 0038) ----------
const EsitoTest = z.object({ superato: z.boolean(), dettagli: z.record(z.unknown()).default({}) });

export const Enunciato = z.object({
  id: z.string().regex(/^e-[a-z0-9-]+$/),
  versione: z.number().int().positive(),
  testo: z.string().min(10).max(160),
  tema: slug,
  livelloGoverno: z.enum(["nazionale", "regionale", "ue"]),
  stato: z.enum(["attivo", "ritirato"]),
  /** Scheda "Prima di rispondere" (ADR 0013): fatto dal voto d'origine e argomenti simmetrici, senza numeri. */
  contesto: z.object({
    fatto: z.string().max(200),
    favorevoli: z.string().max(160),
    contrari: z.string().max(160),
  }),
  origine: z.object({
    votazione: z.object({ ramo: z.enum(["camera", "senato"]), legislatura: z.number().int(), idEsterno: z.string() }),
    atto: z.string().nullable(),
    data: data,
    direzione: z.union([z.literal(1), z.literal(-1)]),
    generazione: z.object({ modello: z.string(), promptVersione: z.string(), inputSha256: z.string() }),
  }),
  test: z.object({
    divisivita: EsitoTest,
    discriminazione: EsitoTest,
    tema: EsitoTest,
    sensibilita: EsitoTest,
    polarita: EsitoTest,
  }),
});

export const Catalogo = z
  .object({
    versione: z.string().regex(/^v\d+$/),
    stato: z.enum(["provvisorio", "definitivo"]),
    nota: z.string(),
    generato_il: z.string(),
    enunciatiPerTema: z.number().int().positive(),
    enunciati: z.array(Enunciato),
  })
  .superRefine((c, ctx) => {
    // ADR 0022: lo stesso numero di domande attive per ogni tema
    const perTema = new Map<string, number>();
    for (const e of c.enunciati.filter((x) => x.stato === "attivo")) perTema.set(e.tema, (perTema.get(e.tema) ?? 0) + 1);
    for (const [tema, n] of perTema)
      if (n !== c.enunciatiPerTema)
        ctx.addIssue({ code: "custom", message: `tema ${tema}: ${n} domande, attese ${c.enunciatiPerTema}` });
    const ids = c.enunciati.map((e) => `${e.id}@${e.versione}`);
    if (new Set(ids).size !== ids.length) ctx.addIssue({ code: "custom", message: "id ripetuti nel catalogo" });
  });

export const SCHEMI = {
  "temi.yaml": Temi,
  "scala.yaml": Scala,
  "parametri.yaml": Parametri,
  "letture.yaml": Letture,
  "governance.yaml": Governance,
  "partiti.yaml": Partiti,
  "gruppi.yaml": Gruppi,
  "perimetro.yaml": Perimetro,
} as const;
