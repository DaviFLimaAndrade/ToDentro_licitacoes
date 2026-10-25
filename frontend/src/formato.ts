export function dataCurta(iso?: string | null): string {
  if (!iso) return "sem data";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

export function valorCurto(v?: number | null): string {
  if (!v) return "valor sigiloso";
  if (v >= 1_000_000) return `R$ ${(v / 1_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mi`;
  if (v >= 1_000) return `R$ ${Math.round(v / 1_000)} mil`;
  return `R$ ${Math.round(v)}`;
}

export function valorCompleto(v?: number | null): string {
  if (!v) return "não informado";
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function encurtar(texto: string | null | undefined, n = 110): string {
  const limpo = (texto ?? "").replace(/\s+/g, " ").trim();
  return limpo.length <= n ? limpo : `${limpo.slice(0, n - 1)}…`;
}

export function diasRestantes(iso?: string | null): number | null {
  if (!iso) return null;
  const fim = new Date(iso).getTime();
  return Number.isNaN(fim) ? null : Math.ceil((fim - Date.now()) / 86_400_000);
}

export function linkPncp(numeroControle: string): string | null {
  const m = numeroControle.match(/^(\d+)-\d+-(\d+)\/(\d{4})$/);
  return m ? `https://pncp.gov.br/app/editais/${m[1]}/${m[3]}/${Number(m[2])}` : null;
}

export const ROTULO = { alta: "Alta aderência", media: "Média aderência", baixa: "Baixa aderência" } as const;
export const ORDEM = { alta: 0, media: 1, baixa: 2 } as const;
