import { pacchetto } from "@/lib/dati";

const MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];
const inParole = (iso: string) => {
  const [a, m, g] = iso.split("-").map(Number);
  return `${g} ${MESI[m! - 1]} ${a}`;
};

/**
 * Con i dati di esempio ogni pagina lo dice (come nei mock): nomi e numeri sono inventati.
 * Con i dati veri, finché i voti non sono tutti caricati, dice fin dove arrivano (ADR 0023: la copertura è sempre dichiarata).
 */
export function NotaEsempio() {
  const { manifest } = pacchetto();
  if (manifest.esempio)
    return (
      <p className="nota esempio">
        Esempio per provare il sito: partiti, nomi e numeri sono inventati. I dati veri arrivano quando avremo finito di
        caricare i voti del Parlamento.
      </p>
    );
  const date = Object.values(manifest.fonti ?? {}).map((f) => f.ultima_votazione).sort();
  const ultima = date[0];
  const giorni = ultima ? (Date.parse(manifest.generato_il) - Date.parse(ultima)) / 86_400_000 : Infinity;
  if (giorni <= 45) return null;
  return (
    <p className="nota esempio">
      {ultima
        ? <>Stiamo ancora caricando i voti del Parlamento: per ora arrivano fino al {inParole(ultima)}. Gli altri arrivano nei prossimi giorni.</>
        : <>Stiamo ancora caricando i voti del Parlamento. I primi dati arrivano nei prossimi giorni.</>}
    </p>
  );
}
