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
      const m = script.match(new RegExp(`const ${n}=([\\s\\S]*?\\n\\]);`));
      if (!m) throw new Error(`${file}: non trovo ${n}`);
      return `${n}=${m[1]};`;
    })
    .join("\n");
  const ctx = {};
  vm.runInNewContext(nomi.map((n) => `var ${n};`).join("") + dichiarazioni, ctx);
  return ctx;
}

const slug = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
const { partiti, politici } = datiDelMock("vista-soggetti.html", ["partiti", "politici"]);
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
const domande = q.domande.map((d, i) => ({
  id: `d${i + 1}`,
  testo: d.t,
  tema: TEMI[i],
  contesto: { fatto: d.c, favorevoli: "", contrari: "" },
}));

// Collegamento tra le domande del questionario e i temi della scheda di Alleanza Progresso
const chiaveScheda = ["Salario minimo", "grandi patrimoni", "Invio di armi", "Cittadinanza", "nucleari", "sanità pubblica", "Pensione", "autonomia"];

const statoPromessa = { f: "mantenuta", m: "a_meta", n: "non_mantenuta" };

function soggettoDa(p, tipo) {
  return {
    id: slug(p.n),
    slug: slug(p.n),
    tipo,
    nome: p.n,
    ruolo: p.r,
    ...(tipo === "persona" && { partito: slug(p.r.split(" · ")[0]) }),
    numeri: { sbagliati: p.sbN, controllati: p.sbD },
    vaghi: { n: p.vagoN, d: p.vagoD },
    coerenza: { contrari: p.votoD - p.votoK, confrontabili: p.votoD },
    promesse: { mantenute: p.prom[0], totali: p.prom[1] },
  };
}

const soggetti = [...partiti.map((p) => soggettoDa(p, "partito")), ...politici.map((p) => soggettoDa(p, "persona"))];

const accostamenti = {};
for (const p of [...partiti, ...politici])
  if (p.ex)
    accostamenti[slug(p.n)] = [
      { detto: p.ex.said, dove: p.ex.dove, vero: p.ex.vero, fonte: p.ex.fonte, esito: "sbagliato", frase: "" },
    ];
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
console.log(`Esempio scritto: ${soggetti.length} soggetti, ${domande.length} domande.`);
