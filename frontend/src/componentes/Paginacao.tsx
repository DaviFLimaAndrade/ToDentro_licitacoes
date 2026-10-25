interface Props {
  pagina: number;
  paginas: number;
  onIr: (p: number) => void;
}

function numeros(pagina: number, paginas: number): (number | "…")[] {
  const set = new Set([1, paginas, pagina - 2, pagina - 1, pagina, pagina + 1, pagina + 2]);
  const lista = [...set].filter((n) => n >= 1 && n <= paginas).sort((a, b) => a - b);
  return lista.flatMap((n, i) => (i > 0 && n - lista[i - 1] > 1 ? ["…" as const, n] : [n]));
}

export function Paginacao({ pagina, paginas, onIr }: Props) {
  if (paginas <= 1) return null;
  return (
    <nav className="paginacao" aria-label="Paginação">
      <button type="button" disabled={pagina === 1} onClick={() => onIr(pagina - 1)}>‹ Anterior</button>
      {numeros(pagina, paginas).map((n, i) =>
        n === "…" ? (
          <span key={`r${i}`} className="reticencias">…</span>
        ) : (
          <button type="button" key={n} className={n === pagina ? "atual" : ""} aria-current={n === pagina ? "page" : undefined} onClick={() => onIr(n)}>
            {n}
          </button>
        ),
      )}
      <button type="button" disabled={pagina === paginas} onClick={() => onIr(pagina + 1)}>Próxima ›</button>
    </nav>
  );
}
