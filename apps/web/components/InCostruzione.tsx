/** Avviso uguale in ogni pagina finché il sito non ha i dati veri (ADR 0036: l'assenza si spiega). */
export function InCostruzione() {
  return (
    <p className="nota">
      Il sito è in costruzione. Nomi e partiti sono veri. I voti in Parlamento li stiamo ancora caricando: dove manca
      un dato lo diciamo, non lo inventiamo.
    </p>
  );
}
