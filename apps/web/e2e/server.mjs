// Server statico minimo per i test: serve out/ come Vercel con cleanUrls (/domande → domande.html).
import { createServer } from "node:http";
import { existsSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

const OUT = path.resolve(import.meta.dirname, "../out");
const TIPI = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".woff2": "font/woff2", ".txt": "text/plain", ".json": "application/json", ".svg": "image/svg+xml", ".ico": "image/x-icon" };
const porta = Number(process.env.PORTA ?? 4310);

createServer((req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  const candidati = [p, `${p}.html`, path.join(p, "index.html")].map((x) => path.join(OUT, x));
  const file = candidati.find((f) => f.startsWith(OUT) && existsSync(f) && statSync(f).isFile());
  if (!file) {
    res.writeHead(404).end("non trovato");
    return;
  }
  res.writeHead(200, { "Content-Type": TIPI[path.extname(file)] ?? "application/octet-stream" }).end(readFileSync(file));
}).listen(porta, () => console.log(`in ascolto su ${porta}`));
