// Formato del pacchetto dati che il sito legge al build (piano §3.9). Uguale per i dati di esempio
// (dati/esempio/) e per i dati veri del rilascio: cambiando pacchetto non cambiano le pagine.
import type { Valore } from "@op/affinita";

export interface Manifest {
  versione: string;
  esempio: boolean;
  generato_il: string;
  catalogo: { versione: string; stato: "provvisorio" | "definitivo" };
  sezioni: { posizioni: boolean; numeri: boolean; coerenza: boolean; promesse: boolean; letture: boolean };
  /** Fin dove arrivano i voti caricati, per ramo (solo nei pacchetti veri). */
  fonti?: Record<string, { legislatura: number; ultima_votazione: string }>;
}

export interface Conteggio { n: number; d: number }

export interface Soggetto {
  id: string;
  slug: string;
  tipo: "partito" | "persona";
  nome: string;
  ruolo: string;
  /** Per le persone: il partito (id), da cui si legge se è al governo. */
  partito?: string;
  numeri?: { sbagliati: number; controllati: number };
  vaghi?: Conteggio;
  coerenza?: { contrari: number; confrontabili: number };
  promesse?: { mantenute: number; totali: number };
  /** Come sono fatte promesse e annunci (ADR 0039); assente finché Laya non è calibrato. */
  indicatori?: { precise: Conteggio; soldi: Conteggio; inTempo: Conteggio; attacchi: Conteggio };
}

export interface Domanda {
  id: string;
  testo: string;
  tema: string;
  contesto: { fatto: string; favorevoli: string; contrari: string };
}

export interface Evidenza { testo: string; quando: string; url?: string }

export interface Posizione {
  valore: Valore | null;
  stato: "documentata" | "non_documentata" | "divergente";
  evidenze: Evidenza[];
  nota?: string;
}

export interface Accostamento {
  detto: string;
  dove: string;
  vero: string;
  fonte: string;
  esito: "sbagliato" | "quasi" | null;
  frase: string;
}

export interface Promessa { stato: "mantenuta" | "a_meta" | "non_mantenuta"; testo: string; motivo: string }

export type MetricaTempo =
  | "vota_con_governo" | "vota_compatto" | "numeri_sbagliati" | "promesse_precise" | "annunci_seguiti" | "frasi_contro";

/** Serie per trimestre (ADR 0040). Un punto con d sotto soglia non si disegna. */
export interface Andamento {
  trimestri: string[]; // "2022-T4", ...
  governo: Record<string, boolean[]>; // per partito, un valore per trimestre
  serie: Record<string, Partial<Record<MetricaTempo, Conteggio[]>>>;
}

export interface Correzione { quando: string; oggetto: string; prima: string; dopo: string; motivo: string }

export interface Pacchetto {
  manifest: Manifest;
  domande: Domanda[];
  soggetti: Soggetto[];
  posizioni: Record<string, Record<string, Posizione>>;
  accostamenti: Record<string, Accostamento[]>;
  promesse: Record<string, Promessa[]>;
  andamento: Andamento;
  correzioni: Correzione[];
}
