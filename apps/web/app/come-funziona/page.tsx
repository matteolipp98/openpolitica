import type { Metadata } from "next";

export const metadata: Metadata = { title: "Come funziona" };

const PASSI = [
  ["Raccogliamo quello che dicono", "Comunicati, interviste, post sui canali ufficiali, interventi in aula. Ogni giorno."],
  ["Controlliamo i numeri", "Se dicono una cifra, andiamo a vedere quella vera sui siti ufficiali: ISTAT, Eurostat, Banca d'Italia, bilancio dello Stato."],
  ["Guardiamo come votano", "Ogni voto in Parlamento è pubblico, nome per nome. Lo confrontiamo con quello che avevano dichiarato."],
  ["Te lo raccontiamo semplice", "Con sotto sempre la data, l'atto e il link, così puoi controllare tu."],
];

const SI = [
  "Controlliamo i numeri che dicono.",
  "Mostriamo come hanno votato, con data e atto.",
  "Segnaliamo quando dicono una cosa e poi votano il contrario.",
  "Ti diciamo chi la pensa come te, se rispondi alle domande.",
];
const NO = [
  "Non ti diciamo per chi votare.",
  "Non diamo voti o pagelle ai politici.",
  "Non giudichiamo se un'idea è giusta o sbagliata: quello dipende da cosa pensi tu.",
  "Non inventiamo niente: se un dato non c'è, scriviamo che non c'è.",
];

const FAQ: [string, string[]][] = [
  ["Siete di destra o di sinistra?", [
    "Né l'una né l'altra, e non ti chiediamo di crederci sulla parola.",
    "Tutto quello che usiamo è pubblico: le domande, i voti che collegiamo a ogni domanda, il modo in cui facciamo i conti. Chiunque può controllare e dirci che abbiamo sbagliato.",
    "Non prendiamo soldi da partiti, candidati o comitati elettorali.",
  ]],
  ["Chi ha scelto le domande?", [
    "Non le abbiamo scritte noi a tavolino. Partiamo dai voti che in Parlamento hanno davvero diviso i partiti, e da quelli ricaviamo le domande.",
    "Così le domande non sono le nostre idee: sono le cose su cui loro si sono già divisi.",
  ]],
  ["Perché a volte scrivete \"non si sa\"?", [
    "Perché su quell'argomento non abbiamo trovato né un voto né una dichiarazione chiara.",
    "Potremmo tirare a indovinare. Preferiamo lasciare vuoto.",
  ]],
  ["Chi decide che un numero è sbagliato?", [
    "Una regola uguale per tutti. Se il numero è solo arrotondato, va bene. Se è troppo lontano da quello vero, è sbagliato.",
    "Prima controlliamo che la frase sia davvero sua. Se abbiamo un dubbio, non diciamo niente.",
  ]],
  ["Perché non dite \"ha mentito\"?", [
    "Perché non possiamo sapere se uno sbaglia apposta o si è confuso.",
    "Ti diciamo solo che il numero è sbagliato e qual è quello vero. Il resto lo giudichi tu.",
  ]],
  ["Le mie risposte dove finiscono?", [
    "Restano sul tuo telefono o sul tuo computer. Non le vediamo e non le salviamo da nessuna parte.",
    "Le tue idee politiche sono fatti tuoi.",
  ]],
  ["Se trovo un errore?", [
    "Scrivici: c'è un modulo per segnalarlo, e vale per tutti, anche per i politici e il loro staff.",
    "Se ci dici che abbiamo sbagliato noi, togliamo quel numero finché non l'abbiamo ricontrollato.",
    "Quando correggiamo qualcosa lo scriviamo in una pagina pubblica, con la data. Non cancelliamo di nascosto.",
  ]],
  ["Usate l'intelligenza artificiale?", [
    "Sì, per leggere tanti documenti e tirarne fuori le frasi dei politici: a mano non ce la faremmo.",
    "Ma i numeri non li scrive mai: quelli arrivano dalle banche dati ufficiali. E il calcolo di chi la pensa come te è una formula fissa, sempre la stessa per tutti.",
  ]],
];

export default function ComeFunziona() {
  return (
    <main>
      <h1>Come funziona</h1>
      <p className="lede">
        In breve: prendiamo quello che i politici dicono, lo confrontiamo con i dati ufficiali e con come votano davvero
        in Parlamento. Poi te lo mostriamo.
      </p>

      <h2>I quattro passaggi</h2>
      {PASSI.map(([t, d], i) => (
        <div className="passo" key={t}>
          <span className="num">{i + 1}</span>
          <div>
            <h3>{t}</h3>
            <p>{d}</p>
          </div>
        </div>
      ))}

      <h2>Un esempio</h2>
      <p>Così controlliamo un numero, passo per passo. L&apos;esempio è inventato, serve solo a spiegare il metodo.</p>
      <div className="conf">
        <div>
          <p className="et">Ha detto</p>
          <p>L&apos;occupazione femminile è cresciuta di oltre un milione di posti.</p>
          <cite>Esempio inventato</cite>
        </div>
        <div>
          <p className="et">Siamo andati a vedere</p>
          <p>I dati ISTAT sul lavoro, stesso periodo: 412.000 posti in più.</p>
          <cite>Esempio inventato</cite>
        </div>
        <div className="esito">
          <b>Numero sbagliato.</b> Il numero vero è meno della metà. Le donne che lavorano sono comunque aumentate.
        </div>
      </div>

      <h2>Cosa facciamo e cosa no</h2>
      <div className="si-no">
        {SI.map((t) => (
          <div className="sn ok" key={t}><span className="seg">Sì</span><p>{t}</p></div>
        ))}
        {NO.map((t) => (
          <div className="sn no" key={t}><span className="seg">No</span><p>{t}</p></div>
        ))}
      </div>

      <h2>Domande che ci fanno</h2>
      {FAQ.map(([q, a]) => (
        <details className="faq" key={q}>
          <summary>{q}</summary>
          <div className="a">{a.map((p) => <p key={p}>{p}</p>)}</div>
        </details>
      ))}

      <h2>Quello che ancora non facciamo</h2>
      <div className="box">
        <p>Non guardiamo i video e la tv: se una cosa la dicono solo in televisione, ci arriva solo se poi un giornale la scrive.</p>
        <p>Seguiamo i partiti principali e i loro leader, non tutti i parlamentari.</p>
        <p>Sulle dichiarazioni partiamo da quando abbiamo acceso il sito. Sui voti in Parlamento invece andiamo indietro di anni.</p>
      </div>
    </main>
  );
}
