"use client";
// Grafico di una serie per trimestre (ADR 0040): punti veri, nessun segmento sopra un buco,
// fascia per i periodi al governo, scala in parole. Tocca un punto per i suoi numeri.
import { useState } from "react";

interface Punto { n: number; d: number; governo: boolean }

export function GraficoTempo({ punti, etichette, minimo, titolo }: {
  punti: Punto[];
  etichette: string[]; // "Aprile – giugno 2024"
  minimo: number;
  titolo: string;
}) {
  const [scelto, setScelto] = useState<number | null>(null);
  const W = 320, H = 118, X0 = 34, X1 = W - 6, Y0 = 8, Y1 = H - 20;
  const x = (i: number) => X0 + ((X1 - X0) * i) / Math.max(1, punti.length - 1);
  const y = (q: number) => Y1 - (Y1 - Y0) * q;
  const ok = (p: Punto) => p.d >= minimo;
  const anni = etichette.map((e, i) => [e, i] as const).filter(([e]) => e.startsWith("Gennaio"));

  return (
    <>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${titolo}: andamento ogni tre mesi`}>
        {punti.map((p, i) =>
          p.governo ? (
            <rect key={`g${i}`} className="fascia"
              x={i ? (x(i - 1) + x(i)) / 2 : X0 - 4} y={Y0} height={Y1 - Y0}
              width={(i < punti.length - 1 ? (x(i) + x(i + 1)) / 2 : X1 + 4) - (i ? (x(i - 1) + x(i)) / 2 : X0 - 4)} />
          ) : null,
        )}
        {([[0, "nessuna"], [0.5, "metà"], [1, "tutte"]] as const).map(([q, t]) => (
          <g key={t}>
            <line className="asse" x1={X0} x2={X1} y1={y(q)} y2={y(q)} />
            <text x={0} y={y(q) + 3}>{t}</text>
          </g>
        ))}
        {anni.map(([e, i]) => <text key={e} x={x(i) - 10} y={H - 4}>{e.slice(-4)}</text>)}
        {punti.map((p, i) => {
          const a = punti[i - 1];
          return i > 0 && a && ok(a) && ok(p) ? (
            <line key={`l${i}`} className="linea" x1={x(i - 1)} y1={y(a.n / a.d)} x2={x(i)} y2={y(p.n / p.d)} />
          ) : null;
        })}
        {punti.map((p, i) =>
          ok(p) ? (
            <g key={`p${i}`} onClick={() => setScelto(i)} style={{ cursor: "pointer" }}>
              <circle className={`punto${scelto === i ? " sel" : ""}`} cx={x(i)} cy={y(p.n / p.d)} r={3.6} />
              <circle className="tocca" cx={x(i)} cy={y(p.n / p.d)} r={11} />
            </g>
          ) : null,
        )}
      </svg>
      <p className="dettaglio" aria-live="polite">
        {scelto === null
          ? "Tocca un punto per vedere i numeri di quei tre mesi."
          : `${etichette[scelto]}: ${punti[scelto]!.n} su ${punti[scelto]!.d} (${Math.round((punti[scelto]!.n / punti[scelto]!.d) * 100)}%).${punti[scelto]!.governo ? " Era al governo." : ""}`}
      </p>
      <details className="numeri">
        <summary>Vedi tutti i numeri</summary>
        <table>
          <thead><tr><th>Periodo</th><th>Volte</th><th>Su</th></tr></thead>
          <tbody>
            {punti.map((p, i) => (
              <tr key={etichette[i]}>
                <td>{etichette[i]}</td>
                <td>{ok(p) ? p.n : "—"}</td>
                <td>{p.d}{ok(p) ? "" : " (troppo pochi)"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </>
  );
}
