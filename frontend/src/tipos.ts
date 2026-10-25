
export interface Perfil {
  nome: string;
  segmento: string;
  palavras_chave: string[];
  uf: string;
  municipio: string | null;
  codigo_municipio_ibge: string | null;
  faixa_valor_min: number | null;
  faixa_valor_max: number | null;
  documentos_que_tem: string[];
  nao_faz: string[];
}

export interface Licitacao {
  numero_controle: string;
  objeto: string;
  orgao?: string;
  municipio?: string;
  uf?: string;
  modalidade?: string;
  valor_estimado?: number;
  data_encerramento?: string;
  link_sistema_origem?: string;
  motivo_triagem?: string;
  tipo_objeto?: "servico" | "material" | "misto" | null;
  me_epp?: "exclusiva" | "parcial" | null;
}

export type Aderencia = "alta" | "media" | "baixa";

export interface Ficha {
  objeto: string | null;
  prazo_proposta: string | null;
  valor_estimado: number | null;
  modalidade: string | null;
  vigencia: string | null;
  exigencias: string[];
  visita_tecnica: string | null;
  trecho_fonte: string | null;
}

export interface Veredito {
  aderencia: Aderencia;
  vale_a_pena: boolean;
  motivo: string;
  bloqueios: string[];
}

export interface Cota {
  usados: number;
  limite: number;
}

export type Uso = Record<"resumo" | "busca", Cota>;

export interface Avaliacao {
  ficha: Ficha;
  veredito: Veredito;
  url_edital: string | null;
  uso?: Uso;
  tempos?: { leitor_s?: number; judge_s?: number; download_s?: number; modo?: "texto" | "pdf"; cache?: number };
}

export type EstadoAvaliacao =
  | { estado: "na-fila" }
  | { estado: "lendo" }
  | { estado: "ok"; dados: Avaliacao }
  | { estado: "erro"; erro: string };

export interface DetalhesBusca {
  params: { palavras_chave?: string[]; abrangencia?: string; municipio?: string | null };
  candidatos: number;
  fora_da_faixa: number;
  descartados_triagem: number;
}

export interface Feed {
  regiao: Licitacao[];
  estado: Licitacao[];
  regiao_nome: string;
  detalhes: { regiao: DetalhesBusca; estado: DetalhesBusca };
}

export interface ResultadoBusca {
  candidatas: Licitacao[];
  detalhes: DetalhesBusca;
  uso?: Uso;
}

export interface PaginaLicitacoes {
  itens: Licitacao[];
  total: number;
  pagina: number;
  paginas: number;
}

export interface Municipio {
  municipio: string;
  codigo_ibge: string;
  total: number;
}

export type Abrangencia = "estado" | "regiao" | "municipio";

export interface FiltrosLista {
  q: string;
  abrangencia: Abrangencia;
  municipio: string;
  dias: number;
  meEpp: boolean;
}

export interface Status {
  escopo: { uf: string; regiao: string; municipios: number; dias_max: number };
  banco: { total: number; ultimo_sync: string; desatualizado: boolean; itens_verificados: number } | null;
}
