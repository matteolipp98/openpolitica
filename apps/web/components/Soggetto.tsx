import Link from "next/link";
import type { SoggettoPagina } from "@/lib/contenuti";

/** Righe del dettaglio: in fase 0 nessuna ha ancora dati, quindi ognuna spiega quando arriveranno. */
const RIGHE = [
  { cosa: "Come ha votato sulle cose che contano", quando: "Arriva quando avremo caricato i voti in Parlamento." },
  { cosa: "Numeri sbagliati", quando: "Arriva quando controlleremo i numeri che dicono." },
  { cosa: "Promesse mantenute", quando: "Arriva quando avremo letto i programmi elettorali." },
];

export function SchedaBreve({ s }: { s: SoggettoPagina }) {
  const href = s.tipo === "partito" ? `/partiti/${s.slug}` : `/persone/${s.slug}`;
  return (
    <details className="card">
      <summary>
        <span className="nome">{s.nome}</span>
        <div className="ruolo">{s.ruolo}</div>
        <p className="frase">Per ora non abbiamo ancora dati da mostrare.</p>
        <span className="apri">
          <span className="chiuso">Vedi i dettagli ▾</span>
          <span className="aperto">Chiudi ▴</span>
        </span>
      </summary>
      <RigheVuote />
      <p className="piccolo">
        <Link href={href}>Apri la scheda</Link>. Qui non diciamo se le sue idee sono buone: quello lo decidi tu.
      </p>
    </details>
  );
}

export function RigheVuote() {
  return (
    <>
      {RIGHE.map((r) => (
        <div className="riga" key={r.cosa}>
          <span className="cifra vuota" aria-hidden="true">—</span>
          <div className="testo">
            <p>{r.cosa}</p>
            <p className="sotto">{r.quando}</p>
          </div>
        </div>
      ))}
    </>
  );
}
