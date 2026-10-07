import { quota } from "@/lib/letture";
import type { Soggetto } from "@/lib/tipi";
import type { Riga } from "@/components/Righe";

/** Righe di dettaglio di un soggetto; quelle senza dati spiegano perché (ADR 0036). */
export function righe(s: Soggetto): Riga[] {
  const out: Riga[] = [];
  if (s.numeri) {
    const q = quota(s.numeri.sbagliati, s.numeri.controllati);
    out.push({ cifra: q.cifra, testo: "Ha detto un dato sbagliato", sotto: `${q.sotto} dati controllati, per esempio su posti di lavoro, prezzi, tasse.${q.pochi}` });
  } else out.push({ cifra: "—", testo: "Ha detto un dato sbagliato", sotto: "Arriva quando controlleremo i dati che dice: posti di lavoro, prezzi, tasse." });
  if (s.vaghi) {
    const q = quota(s.vaghi.n, s.vaghi.d);
    out.push({ cifra: q.cifra, testo: "Frasi vaghe", sotto: `${q.sotto}: niente dati, niente date, niente impegni precisi.${q.pochi}`, ottone: true });
  }
  if (s.coerenza)
    out.push({ cifra: String(s.coerenza.contrari), testo: "Ha detto una cosa e ha votato il contrario", sotto: `Su ${s.coerenza.confrontabili} volte in cui possiamo confrontare` });
  if (s.promesse)
    out.push({ cifra: String(s.promesse.mantenute), testo: "Promesse mantenute", sotto: `Su ${s.promesse.totali} promesse del programma` });
  else out.push({ cifra: "—", testo: "Promesse mantenute", sotto: "Arriva quando avremo letto i programmi elettorali." });
  return out;
}
