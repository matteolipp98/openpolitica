import { quota } from "@/lib/letture";
import type { Soggetto } from "@/lib/tipi";
import type { Riga } from "@/components/Righe";

/** Righe di dettaglio di un soggetto; quelle senza dati spiegano perché (ADR 0036). */
export function righe(s: Soggetto): Riga[] {
  const out: Riga[] = [];
  if (s.numeri) {
    const q = quota(s.numeri.sbagliati, s.numeri.controllati);
    out.push({ cifra: q.cifra, testo: "Numeri sbagliati", sotto: `${q.sotto} controllati` });
  } else out.push({ cifra: "—", testo: "Numeri sbagliati", sotto: "Arriva quando controlleremo i numeri che dice." });
  if (s.vaghi) {
    const q = quota(s.vaghi.n, s.vaghi.d);
    out.push({ cifra: q.cifra, testo: "Frasi che non si possono controllare", sotto: `${q.sotto}: niente numeri, niente date, niente impegni precisi`, ottone: true });
  }
  if (s.coerenza)
    out.push({ cifra: String(s.coerenza.contrari), testo: "Volte in cui ha votato al contrario di quello che diceva", sotto: `Su ${s.coerenza.confrontabili} occasioni in cui possiamo confrontare` });
  if (s.promesse)
    out.push({ cifra: String(s.promesse.mantenute), testo: "Promesse mantenute", sotto: `Su ${s.promesse.totali} promesse del programma` });
  else out.push({ cifra: "—", testo: "Promesse mantenute", sotto: "Arriva quando avremo letto i programmi elettorali." });
  return out;
}
