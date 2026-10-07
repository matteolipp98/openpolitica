export interface Riga { cifra: string; testo: string; sotto: string; ottone?: boolean }

export function Righe({ righe }: { righe: Riga[] }) {
  return (
    <>
      {righe.map((r) => (
        <div className="riga" key={r.testo}>
          <span className={`cifra${r.ottone ? " b" : ""}${r.cifra === "—" ? " vuota" : ""}`}>{r.cifra}</span>
          <div className="testo">
            <p>{r.testo}</p>
            <p className="sotto">{r.sotto}</p>
          </div>
        </div>
      ))}
    </>
  );
}
