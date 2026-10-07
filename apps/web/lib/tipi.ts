// Formato del pacchetto dati che il sito legge al build (piano §3.9). Uguale per i dati di esempio
// (dati/esempio/) e per i dati veri del rilascio: cambiando pacchetto non cambiano le pagine.
import type { Valore } from "@op/affinita";

export interface Manifest {
  versione: string;
  esempio: boolean;
  generato_il: string;
  catalogo: { versione: string; stato: "provvisorio" | "definitivo" };
  sezioni: { posizioni: boolean; numeri: boolean; coerenza: boolean; promesse: boolean; letture: boolean };
}

export interface Conteggio { n: number; d: number }

export interface Soggetto {
  id: string;
  slug: string;
  tipo: "partito" | "persona";
  nome: string;
  ruolo: string;
  numeri?: { sbagliati: number; controllati: number };
  vaghi?: Conteggio;
  coerenza?: { contrari: number; confrontabili: number };
  promesse?: { mantenute: number; totali: number };
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

export interface Pacchetto {
  manifest: Manifest;
  domande: Domanda[];
  soggetti: Soggetto[];
  posizioni: Record<string, Record<string, Posizione>>;
  accostamenti: Record<string, Accostamento[]>;
  promesse: Record<string, Promessa[]>;
}
