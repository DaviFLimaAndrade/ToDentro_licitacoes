import type {
  Avaliacao, Feed, FiltrosLista, Municipio, PaginaLicitacoes, Perfil, ResultadoBusca, Status, Uso,
} from "./tipos";

async function pedir<T>(caminho: string, corpo?: unknown): Promise<T> {
  const resp = await fetch(caminho, {
    method: corpo === undefined ? "GET" : "POST",
    headers: corpo === undefined ? undefined : { "Content-Type": "application/json" },
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
  });
  if (!resp.ok) {
    const detalhe = await resp.json().catch(() => null);
    throw new Error(detalhe?.detail ?? `Erro ${resp.status}`);
  }
  return resp.json() as Promise<T>;
}

export const api = {
  status: () => pedir<Status>("/api/status"),
  uso: () => pedir<Uso>("/api/uso"),
  perfil: () => pedir<Perfil>("/api/perfil"),
  licitacoes: (f: FiltrosLista, pagina: number, tamanho: number) => {
    const p = new URLSearchParams({ pagina: String(pagina), tamanho: String(tamanho), abrangencia: f.abrangencia });
    if (f.q.trim()) p.set("q", f.q.trim());
    if (f.abrangencia === "municipio" && f.municipio) p.set("municipio", f.municipio);
    if (f.dias) p.set("dias", String(f.dias));
    if (f.meEpp) p.set("me_epp", "true");
    return pedir<PaginaLicitacoes>(`/api/licitacoes?${p}`);
  },
  municipios: () => pedir<Municipio[]>("/api/municipios"),
  feed: (perfil: Perfil) => pedir<Feed>("/api/feed", { perfil }),
  buscar: (pergunta: string, perfil: Perfil) => pedir<ResultadoBusca>("/api/buscar", { pergunta, perfil }),
  avaliar: (numero_controle: string, perfil: Perfil) =>
    pedir<Avaliacao>("/api/avaliar", { numero_controle, perfil }),
};
