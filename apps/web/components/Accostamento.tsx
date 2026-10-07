import type { Accostamento as A } from "@/lib/tipi";

/** "Ha detto / In realtà" con la riga di esito in linguaggio comune (ADR 0036, 0037). */
export function Accostamento({ a }: { a: A }) {
  return (
    <div className="conf">
      <div>
        <p className="et">Ha detto</p>
        <p>{a.detto}</p>
        <cite>{a.dove}</cite>
      </div>
      <div>
        <p className="et">In realtà</p>
        <p>{a.vero}</p>
        <cite>{a.fonte}</cite>
      </div>
      {(a.esito || a.frase) && (
        <div className="esito">
          {a.esito === "sbagliato" && <b>Dato sbagliato. </b>}
          {a.esito === "quasi" && <b>Quasi giusto. </b>}
          {a.frase.replace(/^(Numero|Dato) sbagliato\.\s*|^Sbagliato\.\s*/, "")}
        </div>
      )}
    </div>
  );
}
