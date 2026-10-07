import { pacchetto } from "@/lib/dati";

/** Con i dati di esempio ogni pagina lo dice (come nei mock): nomi e numeri sono inventati. */
export function NotaEsempio() {
  if (!pacchetto().manifest.esempio) return null;
  return (
    <p className="nota esempio">
      Esempio per provare il sito: partiti, nomi e numeri sono inventati. I dati veri arrivano quando avremo finito di
      caricare i voti del Parlamento.
    </p>
  );
}
