// Genera il pacchetto dati di esempio (dati/esempio/*.json) dai dati scritti nei mock in adr/mockup/.
// Nomi e numeri sono inventati, come nei mock. Stesso formato del pacchetto dei dati veri (lib/tipi.ts).
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import vm from "node:vm";

const MOCK = path.resolve(import.meta.dirname, "../../../adr/mockup");
const OUT = path.resolve(import.meta.dirname, "../dati/esempio");

/** Esegue le dichiarazioni `const nome=...;` dello script di un mock e restituisce i valori. */
function datiDelMock(file, nomi) {
  const html = readFileSync(path.join(MOCK, file), "utf8");
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const dichiarazioni = nomi
    .map((n) => {
      const m = script.match(new RegExp(`const ${n}=(\\[[^\\n]*\\]|[\\s\\S]*?\\n\\]);`));
      if (!m) throw new Error(`${file}: non trovo ${n}`);
      return `${n}=${m[1]};`;
    })
    .join("\n");
  const ctx = {};
  vm.runInNewContext(nomi.map((n) => `var ${n};`).join("") + dichiarazioni, ctx);
  return ctx;
}

const slug = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
const leggiEsempio = (f) => JSON.parse(readFileSync(path.join(OUT, f), "utf8"));
// La home (vista-soggetti, rivista con #76) ha i dati dei partiti; le persone e i numeri controllati non sono più
// in nessun mock: restano quelli già scritti nell'esempio.
const home = datiDelMock("vista-soggetti.html", ["ACCORDO", "partiti"]);
const q = datiDelMock("vista-questionario.html", ["domande", "partiti"]);
const scheda = datiDelMock("vista-partito.html", ["temi", "promesse", "numeri", "kpi"]);

/** Esegue la parte pura dello script del mock dell'andamento (fino al calcolo della frase) e ne prende le serie. */
function andamentoDalMock() {
  const html = readFileSync(path.join(MOCK, "vista-andamento.html"), "utf8");
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const puro = script.slice(0, script.indexOf("/* intervallo di Wilson"));
  return vm.runInNewContext(puro + ";({TRIM,partiti,metriche,serie})", {});
}

// Temi delle domande del mock, nello stesso ordine
const TEMI = ["economia", "economia", "esteri", "diritti", "ambiente", "welfare", "economia", "esteri"];
// Giorno e ramo del voto di ogni domanda (inventati): le tre più recenti su temi diversi vanno nella home
const VOTATA = [["2023-03-15", "camera"], ["2025-11-20", "senato"], ["2024-02-10", "camera"], ["2026-05-14", "senato"],
  ["2025-07-02", "camera"], ["2026-09-24", "camera"], ["2026-07-15", "senato"], ["2023-10-05", "senato"]];
const domande = q.domande.map((d, i) => ({
  id: `d${i + 1}`,
  testo: d.t,
  tema: TEMI[i],
  contesto: { fatto: d.c, favorevoli: "", contrari: "" },
  data: VOTATA[i][0],
  ramo: VOTATA[i][1],
}));

// Collegamento tra le domande del questionario e i temi della scheda di Alleanza Progresso
const chiaveScheda = ["Salario minimo", "grandi patrimoni", "Invio di armi", "Cittadinanza", "nucleari", "sanità pubblica", "Pensione", "autonomia"];

const statoPromessa = { f: "mantenuta", m: "a_meta", n: "non_mantenuta" };

// Temi della home, nell'ordine del mock (content/temi.yaml più "altro")
const TEMI_HOME = ["economia", "welfare", "diritti", "ambiente", "istituzioni", "esteri", "altro"];
const prima = leggiEsempio("soggetti.json");
const nomi = Object.fromEntries(home.partiti.map((p) => [slug(p.n), p.n]));
const persone = Object.fromEntries(prima.filter((s) => s.tipo === "persona").map((s) => [s.nome, s]));

const soggettiPartiti = home.partiti.map((p) => {
  const id = slug(p.n);
  const base = prima.find((s) => s.id === id) ?? { id, slug: id, tipo: "partito", nome: p.n };
  const comuni = p.comune ? home.partiti.filter((x) => x.comune && x !== p).map((x) => slug(x.n)) : [];
  return {
    ...base,
    ruolo: p.gov ? "Al governo" : "All'opposizione",
    guida: p.guida.split(" e ").map((nome) => (persone[nome] ? { nome, slug: persone[nome].slug } : { nome })),
    programma: {
      elezione: "2022-09-25",
      promesse: p.prog.reduce((a, b) => a + b, 0),
      precise: { n: p.precise[0], d: p.precise[1] },
      temi: Object.fromEntries(TEMI_HOME.map((t, i) => [t, p.prog[i]])),
      ...(comuni.length && { comune: { stesso_documento: comuni, testo_uguale: [] } }),
    },
  };
});
// Chi guida un partito nella home è iscritto a quel partito anche nella scheda della persona
const guidaDi = Object.fromEntries(home.partiti.flatMap((p) => p.guida.split(" e ").map((n) => [n, slug(p.n)])));
const soggettiPersone = prima.filter((s) => s.tipo === "persona").map((s) => {
  const partito = guidaDi[s.nome] ?? s.partito;
  const carica = s.ruolo.split(" · ")[1];
  return { ...s, partito, ruolo: carica ? `${nomi[partito]} · ${carica}` : nomi[partito] };
});
const soggetti = [...soggettiPartiti, ...soggettiPersone];

const accostamenti = leggiEsempio("accostamenti.json");
// La scheda di Alleanza Progresso ha più confronti, con il loro esito
accostamenti["alleanza-progresso"] = scheda.numeri.map((n) => ({
  detto: n.said,
  dove: n.dove,
  vero: n.vero,
  fonte: n.fonte,
  esito: /(Numero|Dato) sbagliato|Sbagliato/.test(n.esito) ? "sbagliato" : null,
  frase: n.esito.replace(/<[^>]+>/g, ""),
}));

// Posizioni: dal questionario per tutti i partiti; per Alleanza Progresso con i voti della scheda
const posizioni = {};
for (const p of q.partiti) {
  const id = slug(p.n);
  posizioni[id] = {};
  p.p.forEach((v, i) => {
    const d = domande[i];
    const voce = { valore: v, stato: v === null ? "non_documentata" : "documentata", evidenze: [] };
    if (v !== null)
      voce.evidenze.push({
        testo: v > 0 ? "Ha votato a favore" : v < 0 ? "Ha votato contro" : "Il partito si è diviso nel voto",
        quando: "Voto di esempio",
      });
    if (id === "alleanza-progresso") {
      const t = scheda.temi.find((x) => x.q.includes(chiaveScheda[i]) || chiaveScheda[i].includes(x.q));
      if (t) {
        voce.evidenze = t.voti.map((x) => ({ testo: x.t, quando: x.d }));
        if (t.nota) voce.nota = t.nota;
      }
    }
    posizioni[id][d.id] = voce;
  });
}

const promesse = {
  "alleanza-progresso": scheda.promesse.map((p) => ({ stato: statoPromessa[p.s], testo: p.t, motivo: p.n })),
};

// Andamento nel tempo (ADR 0040): stesse serie del mock, con gli id veri delle metriche
const ID_METRICA = { gov: "vota_con_governo", compatto: "vota_compatto", numeri: "numeri_sbagliati",
  precise: "promesse_precise", seguiti: "annunci_seguiti", contro: "frasi_contro" };
const am = andamentoDalMock();
const andamento = {
  trimestri: am.TRIM.map((t) => `${t.a}-T${t.t}`),
  governo: Object.fromEntries(am.partiti.map((p) => [slug(p.n), am.TRIM.map((_, i) => p.gov(i))])),
  serie: Object.fromEntries(am.partiti.map((p) => [slug(p.n),
    Object.fromEntries(am.metriche.map((m) => [ID_METRICA[m.id], am.serie(p, m)]))])),
};

// Come sono fatte promesse e annunci (ADR 0039): solo Alleanza Progresso, come nel mock
const conta = (s) => { const m = s.match(/(\d+)(?: \w+)? su (\d+)/); return { n: +m[1], d: +m[2] }; };
const ap = soggetti.find((s) => s.id === "alleanza-progresso");
ap.indicatori = {
  precise: conta(scheda.kpi[0].s), soldi: conta(scheda.kpi[1].s), inTempo: conta(scheda.kpi[2].s), attacchi: conta(scheda.kpi[3].s),
};

// Il Parlamento oggi: seggi del mock più qualche parlamentare nel gruppo misto. Nel mock i seggi riempiono tutta
// l'aula (al Senato anche di più): l'eccesso si toglie al partito più grande, così i conti tornano.
const TOTALE = { camera: 400, senato: 200 };
const MISTO = { camera: 8, senato: 6 };
const parlamento = {
  data: "2026-10-06",
  rami: Object.fromEntries(Object.entries(TOTALE).map(([ramo, totale]) => {
    const partiti = Object.fromEntries(home.partiti.map((p) => [slug(p.n), p.seggi[ramo]]));
    const eccesso = Object.values(partiti).reduce((a, b) => a + b, 0) + MISTO[ramo] - totale;
    const grande = Object.keys(partiti).reduce((a, b) => (partiti[b] > partiti[a] ? b : a));
    partiti[grande] -= eccesso;
    return [ramo, { totale, partiti, altri: MISTO[ramo] }];
  })),
};

const manifest = {
  versione: "esempio",
  esempio: true,
  generato_il: new Date().toISOString().slice(0, 10),
  catalogo: { versione: "esempio", stato: "provvisorio" },
  sezioni: { posizioni: true, numeri: true, coerenza: true, promesse: true, letture: true },
};

mkdirSync(OUT, { recursive: true });
const scrivi = (f, d) => writeFileSync(path.join(OUT, f), JSON.stringify(d, null, 1) + "\n");
scrivi("manifest.json", manifest);
scrivi("domande.json", domande);
scrivi("soggetti.json", soggetti);
scrivi("posizioni.json", posizioni);
scrivi("accostamenti.json", accostamenti);
scrivi("promesse.json", promesse);
scrivi("andamento.json", andamento);
scrivi("correzioni.json", []);
scrivi("parlamento.json", parlamento);
console.log(`Esempio scritto: ${soggetti.length} soggetti, ${domande.length} domande.`);
