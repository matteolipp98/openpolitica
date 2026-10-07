import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Chi la pensa come te" };

export default function Domande() {
  return (
    <main>
      <h1>Chi la pensa come te</h1>
      <p className="lede">
        Ti faremo alcune domande. Poi ti diremo chi ha votato come la pensi tu, e su cosa invece non siete d&apos;accordo.
      </p>
      <div className="box">
        <p>
          <b>Le domande non sono ancora pronte.</b>
        </p>
        <p>Non le scriviamo noi: le ricaviamo dai voti che in Parlamento hanno davvero diviso i partiti.</p>
        <p>Prima dobbiamo caricare tutti quei voti. Poi controlliamo che ogni domanda sia scritta in modo giusto per tutti.</p>
      </div>
      <p className="chiusura">
        Le tue risposte resteranno sul tuo telefono o sul tuo computer. <Link href="/come-funziona">Come funziona</Link>
      </p>
    </main>
  );
}
