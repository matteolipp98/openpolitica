"use client";
// "Hai trovato un errore?" (ADR 0012, #26). Chiama public.segnala su Supabase con la chiave pubblica:
// la funzione salva la segnalazione e blocca gli abusi. Senza configurazione (esempio, locale) non si mostra.
import { useState } from "react";

const URL_SUPABASE = process.env.NEXT_PUBLIC_SUPABASE_URL?.replace(/\/$/, "");
const CHIAVE = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

type Stato = "chiuso" | "aperto" | "invio" | "fatto" | "errore";

export function Segnala({ dove }: { dove: string }) {
  const [stato, setStato] = useState<Stato>("chiuso");
  const [messaggio, setMessaggio] = useState("");
  if (!URL_SUPABASE || !CHIAVE) return null;

  async function invia(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setStato("invio");
    try {
      const r = await fetch(`${URL_SUPABASE}/rest/v1/rpc/segnala`, {
        method: "POST",
        headers: { apikey: CHIAVE!, "Content-Type": "application/json" },
        body: JSON.stringify({
          p_url: dove,
          p_testo: String(f.get("testo") ?? ""),
          p_contatto: String(f.get("contatto") ?? ""),
          p_trappola: String(f.get("sito") ?? ""),
        }),
      });
      if (r.ok) {
        setStato("fatto");
        return;
      }
      const corpo = await r.json().catch(() => ({}));
      setMessaggio(
        /troppe/.test(corpo.message ?? "") ? "Hai mandato troppe segnalazioni di seguito. Riprova tra un'ora." : "Non siamo riusciti a inviarla. Riprova tra poco.",
      );
      setStato("errore");
    } catch {
      setMessaggio("Non siamo riusciti a inviarla. Controlla la connessione e riprova.");
      setStato("errore");
    }
  }

  if (stato === "chiuso")
    return (
      <p className="segnala-apri">
        <button type="button" className="link-bottone" onClick={() => setStato("aperto")}>Hai trovato un errore? Dicci cosa non va</button>
      </p>
    );
  if (stato === "fatto")
    return <p className="segnala-esito">Grazie. Ricontrolliamo e, se abbiamo sbagliato, lo correggiamo e lo scriviamo nella pagina delle correzioni.</p>;
  return (
    <form className="segnala" onSubmit={invia}>
      <label>
        Cosa non va?
        <textarea name="testo" required minLength={10} maxLength={4000} rows={4} placeholder="Per esempio: questo voto non è del 2023, è del 2024." />
      </label>
      <label>
        Come ti ricontattiamo (facoltativo)
        <input name="contatto" maxLength={200} placeholder="email o telefono" />
      </label>
      {/* Campo trappola: nascosto alle persone, i programmi automatici lo riempiono */}
      <input name="sito" tabIndex={-1} autoComplete="off" aria-hidden="true" className="trappola" />
      <p className="sotto">Vale per tutti, anche per i politici e il loro staff. Non salviamo il tuo indirizzo internet.</p>
      {stato === "errore" && <p className="segnala-errore">{messaggio}</p>}
      <button type="submit" disabled={stato === "invio"}>{stato === "invio" ? "Invio…" : "Invia la segnalazione"}</button>
    </form>
  );
}
