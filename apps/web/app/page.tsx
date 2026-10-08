// La home presenta i partiti (mock adr/mockup/vista-soggetti.html, ADR 0036, issue #76).
import Link from "next/link";
import { NotaEsempio } from "@/components/NotaEsempio";
import { Parlamento } from "@/components/Parlamento";
import { SchedaPartito } from "@/components/SchedaPartito";
import { contenuto, pacchetto, partiti } from "@/lib/dati";
import { colori, domandeHome, votiFinoAl } from "@/lib/home";
import type { TemaPromessa } from "@/lib/tipi";

interface Temi { temi: { id: TemaPromessa; nome: string }[] }

export default function Home() {
  const { domande, posizioni, parlamento, manifest } = pacchetto();
  const lista = partiti(); // in ordine alfabetico (ADR 0009)
  const colore = colori(lista);
  const nomi = Object.fromEntries(lista.map((p) => [p.id, p.nome]));
  // I temi sempre nello stesso ordine: quelli del questionario, poi "Altro"
  const temi = [...contenuto<Temi>("temi.yaml").temi.map((t) => ({ id: t.id, nome: t.nome })), { id: "altro" as const, nome: "Altro" }];
  const tre = manifest.sezioni.posizioni ? domandeHome(domande) : [];
  const votiFino = votiFinoAl();

  return (
    <main className="home">
      <h1>Cosa hanno fatto davvero</h1>
      <p className="lede">Chi c&apos;è in Parlamento, cosa ha promesso, come ha votato. Gli stessi fatti per tutti i partiti: il giudizio è tuo.</p>
      <NotaEsempio />

      {domande.length > 0 && (
        <section className="card invito">
          <h2>Chi la pensa come te?</h2>
          <p>Rispondi a {domande.length} domande su leggi votate davvero. Ti diciamo quali partiti hanno votato come la pensi tu. Ci vogliono pochi minuti, e le risposte restano sul tuo telefono.</p>
          <Link className="bottone" href="/domande">Inizia le domande</Link>
        </section>
      )}

      {parlamento && (
        <>
          <h2 id="titolo-aula">Il Parlamento oggi</h2>
          <p className="sottotitolo">Quanti seggi ha ogni partito, e chi sostiene il governo.</p>
          <Parlamento dati={parlamento} partiti={lista} colore={colore} />
        </>
      )}

      <h2>I partiti</h2>
      <p className="sottotitolo">In ordine alfabetico. Per ogni partito: di cosa parla il suo programma, come ha votato, due numeri.</p>
      <div className="schede">
        {lista.map((p) => (
          <SchedaPartito key={p.id} p={p} colore={colore[p.id]!} temi={temi} nomi={nomi} domande={tre}
            posizioni={posizioni[p.id] ?? {}} votiFino={votiFino} />
        ))}
      </div>
      {tre.length > 0 && (
        <>
          <p className="regola"><b>Quali voti mostriamo.</b> Le stesse {tre.length} domande per tutti i partiti: le domande del questionario votate più di recente, una per tema. Le altre sono nella scheda di ogni partito.</p>
          <details className="cosa">
            <summary>Cosa vogliono dire «Sì» e «No»</summary>
            <p>«Sì» vuol dire che il partito ha votato per quello che dice la frase. «No» vuol dire che ha votato contro. «Né sì né no» vuol dire che si è astenuto, oppure che i suoi parlamentari non hanno votato quasi tutti allo stesso modo.</p>
          </details>
        </>
      )}
      <p className="regola">Qui non diciamo se le idee di un partito sono buone: quello lo decidi tu. <Link href="/metodo#prima-pagina">Come contiamo</Link></p>
    </main>
  );
}
