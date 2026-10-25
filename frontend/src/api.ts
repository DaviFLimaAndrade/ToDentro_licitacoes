import type {
  Avaliacao, Feed, FiltrosLista, Municipio, PaginaLicitacoes, Perfil, ResultadoBusca, Status, Uso,
} from "./tipos";

const SEM_CONEXAO = "Não foi possível falar com o Radar. Confira sua internet e recarregue a página.";

function mensagemPorStatus(status: number): string {
  if (status === 429) return "Muitas tentativas seguidas. Espere um minuto e tente de novo.";
  if (status >= 500) return "O Radar está instável agora. Tente de novo em alguns minutos.";
  return "Não foi possível concluir esta ação. Recarregue a página e tente de novo.";
}

async function pedir<T>(caminho: string, corpo?: unknown): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(caminho, {
      method: corpo === undefined ? "GET" : "POST",
      headers: corpo === undefined ? undefined : { "Content-Type": "application/json" },
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    });
  } catch {
    throw new Error(SEM_CONEXAO);
  }
  if (!resp.ok) {
    const detalhe = await resp.json().catch(() => null);
    throw new Error(typeof detalhe?.detail === "string" ? detalhe.detail : mensagemPorStatus(resp.status));
  }
  try {
    return (await resp.json()) as T;
  } catch {
    throw new Error(mensagemPorStatus(500));
  }
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
  avaliar: (numero_controle: string, perfil: Perfil | null) =>
    pedir<Avaliacao>("/api/avaliar", { numero_controle, perfil }),
};
