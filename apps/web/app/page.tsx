import { Elenco } from "@/components/Elenco";
import { InCostruzione } from "@/components/InCostruzione";
import { partiti, persone } from "@/lib/contenuti";

export default function Indice() {
  return (
    <main>
      <h1>Cosa hanno fatto davvero</h1>
      <p className="lede">Controlliamo i numeri che dicono e li confrontiamo con come votano in Parlamento. Tutto qui.</p>
      <InCostruzione />
      <h2>Tutti</h2>
      <Elenco partiti={partiti()} persone={persone()} />
    </main>
  );
}
