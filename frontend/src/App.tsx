import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import { Cartao } from "./componentes/Cartao";
import { Paginacao } from "./componentes/Paginacao";
import { BarraProgresso } from "./componentes/BarraProgresso";
import { PainelPerfil } from "./componentes/PainelPerfil";
import { Tutorial } from "./componentes/Tutorial";
import { diasRestantes } from "./formato";
import type {
  EstadoAvaliacao, Feed, FiltrosLista, Licitacao, Municipio, PaginaLicitacoes, Perfil, ResultadoBusca, Status, Uso,
} from "./tipos";

const POR_PAGINA = 20;
const PERFIL_VAZIO: Perfil = {
  nome: "", segmento: "", palavras_chave: [], uf: "SP", municipio: null, codigo_municipio_ibge: null,
  faixa_valor_min: null, faixa_valor_max: null, documentos_que_tem: [], nao_faz: [],
};
const FILTROS_INICIAIS: FiltrosLista = { q: "", abrangencia: "estado", municipio: "", dias: 0, meEpp: false };
type Aba = "todas" | "para-voce";

const guardado = {
  ler<T>(chave: string): T | null {
    try {
      const v = localStorage.getItem(chave);
      return v ? (JSON.parse(v) as T) : null;
    } catch {
      return null;
    }
  },
  gravar(chave: string, valor: unknown) {
    try {
      localStorage.setItem(chave, JSON.stringify(valor));
    } catch {
    }
  },
};

export function App() {
  const [perfil, setPerfil] = useState<Perfil | null>(() => guardado.ler<Perfil>("radar.perfil"));
  const [rascunho, setRascunho] = useState<Perfil>(PERFIL_VAZIO);
  const perfilSalvo = perfil !== null;
  const [status, setStatus] = useState<Status | null>(null);
  const [uso, setUso] = useState<Uso | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aba, setAba] = useState<Aba>("todas");

  const [filtros, setFiltros] = useState<FiltrosLista>(FILTROS_INICIAIS);
  const [textoBusca, setTextoBusca] = useState("");
  const [pagina, setPagina] = useState(1);
  const [lista, setLista] = useState<PaginaLicitacoes | null>(null);
  const [carregandoLista, setCarregandoLista] = useState(false);
  const [municipios, setMunicipios] = useState<Municipio[]>([]);

  const [feed, setFeed] = useState<Feed | null>(null);
  const [carregandoFeed, setCarregandoFeed] = useState(false);
  const [busca, setBusca] = useState<{ pergunta: string; inicio: number; resultado?: ResultadoBusca; erro?: string } | null>(null);
  const [inicioFeed, setInicioFeed] = useState(0);
  const [textoIa, setTextoIa] = useState("");
  const perfilDoFeed = useRef("");

  const [avaliacoes, setAvaliacoes] = useState<Record<string, EstadoAvaliacao>>({});
  const [abertos, setAbertos] = useState<Set<string>>(new Set());
  const [painelAberto, setPainelAberto] = useState(false);
  const [tutorial, setTutorial] = useState(false);
  const [filtrosAbertos, setFiltrosAbertos] = useState(false);
  const botaoPerfil = useRef<HTMLButtonElement>(null);
  const topoLista = useRef<HTMLDivElement>(null);
  const fila = useRef<Promise<void>>(Promise.resolve());

  useEffect(() => {
    api.status().then(setStatus).catch((e: Error) => setErro(`Não consegui falar com a API (${e.message}).`));
    api.uso().then(setUso).catch(() => setUso(null));
    api.municipios().then(setMunicipios).catch(() => setMunicipios([]));
  }, []);

  useEffect(() => {
    let atual = true;
    setCarregandoLista(true);
    api.licitacoes(filtros, pagina, POR_PAGINA)
      .then((r) => atual && setLista(r))
      .catch((e: Error) => atual && setErro(e.message))
      .finally(() => atual && setCarregandoLista(false));
    return () => {
      atual = false;
    };
  }, [filtros, pagina]);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).has("tutorial")) {
      setTutorial(true);
      return;
    }
    if (perfilSalvo || guardado.ler<boolean>("radar.tutorialVisto")) return;
    const aoRolar = () => {
      if (window.scrollY > 160) {
        setTutorial(true);
        window.removeEventListener("scroll", aoRolar);
      }
    };
    window.addEventListener("scroll", aoRolar, { passive: true });
    return () => window.removeEventListener("scroll", aoRolar);
  }, [perfilSalvo]);

  const fecharTutorial = useCallback(() => {
    setTutorial(false);
    guardado.gravar("radar.tutorialVisto", true);
  }, []);

  const carregarFeed = useCallback((p: Perfil) => {
    setCarregandoFeed(true);
    setInicioFeed(Date.now());
    perfilDoFeed.current = JSON.stringify(p);
    api.feed(p).then(setFeed).catch((e: Error) => setErro(e.message)).finally(() => setCarregandoFeed(false));
  }, []);

  function abrirAba(nova: Aba) {
    setAba(nova);
    if (nova === "para-voce" && perfil && !feed && !carregandoFeed) carregarFeed(perfil);
  }

  function abrirPerfil() {
    setRascunho(perfil ?? PERFIL_VAZIO);
    setPainelAberto(true);
    fecharTutorial();
  }

  function salvarPerfil() {
    if (!rascunho.segmento.trim()) return;
    guardado.gravar("radar.perfil", rascunho);
    setPerfil(rascunho);
    setPainelAberto(false);
    if (aba === "para-voce" || feed) carregarFeed(rascunho);
  }

  function irParaPagina(p: number) {
    setPagina(p);
    topoLista.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function mudarFiltros(f: Partial<FiltrosLista>) {
    setFiltros((atual) => ({ ...atual, ...f }));
    setPagina(1);
  }

  function resumir(numero: string) {
    const p = perfil;
    setAvaliacoes((a) => ({ ...a, [numero]: { estado: "na-fila" } }));
    fila.current = fila.current.then(async () => {
      setAvaliacoes((a) => ({ ...a, [numero]: { estado: "lendo", inicio: Date.now() } }));
      try {
        const dados = await api.avaliar(numero, p);
        if (dados.uso) setUso(dados.uso);
        setAvaliacoes((a) => ({ ...a, [numero]: { estado: "ok", dados } }));
        setAbertos((s) => new Set(s).add(numero));
      } catch (e) {
        setAvaliacoes((a) => ({ ...a, [numero]: { estado: "erro", erro: (e as Error).message } }));
        api.uso().then(setUso).catch(() => undefined);
      }
    });
  }

  function alternar(numero: string) {
    setAbertos((s) => {
      const novo = new Set(s);
      if (novo.has(numero)) novo.delete(numero);
      else novo.add(numero);
      return novo;
    });
  }

  async function procurarComIa(pergunta: string) {
    if (!perfil || !pergunta.trim()) return;
    const inicio = Date.now();
    setBusca({ pergunta, inicio });
    try {
      const resultado = await api.buscar(pergunta, perfil);
      if (resultado.uso) setUso(resultado.uso);
      setBusca({ pergunta, inicio, resultado });
    } catch (e) {
      setBusca({ pergunta, inicio, erro: (e as Error).message });
      api.uso().then(setUso).catch(() => undefined);
    }
  }

  const grade = (itens: Licitacao[]) => (
    <div className="grade">
      {itens.map((l) => (
        <Cartao
          key={l.numero_controle}
          licitacao={l}
          avaliacao={avaliacoes[l.numero_controle]}
          aberto={abertos.has(l.numero_controle)}
          onResumir={() => resumir(l.numero_controle)}
          resumosRestantes={uso ? uso.resumo.limite - uso.resumo.usados : null}
          onPedirPerfil={abrirPerfil}
          onAlternar={() => alternar(l.numero_controle)}
        />
      ))}
    </div>
  );

  const municipiosComAbertas = useMemo(() => municipios.filter((m) => m.total > 0), [municipios]);
  const perfilMudou = perfil !== null && feed !== null && JSON.stringify(perfil) !== perfilDoFeed.current;

  const prazos = [
    [0, "Qualquer"],
    [3, "3 dias"],
    [7, "7 dias"],
    [15, "15 dias"],
    [30, "30 dias"],
  ] as const;
  const ondes = [
    ["estado", `Todo o estado de ${status?.escopo.uf ?? "SP"}`],
    ["regiao", status?.escopo.regiao ?? "Campinas e região"],
    ["municipio", "Um município"],
  ] as const;

  return (
    <div className="app">
      <header className="barra-topo">
        <div className="barra-topo-dentro">
          <div className="marca">
            <span className="marca-nome">Radar de Licitações</span>
            <span className="marca-sub">PNCP · dados reais</span>
          </div>
          <div className="topo-acoes">
            {uso && <Limites uso={uso} />}
            <button
              type="button"
              ref={botaoPerfil}
              className={perfilSalvo ? "botao-topo" : "botao-vermelho"}
              onClick={abrirPerfil}
            >
              {perfilSalvo ? "Perfil da empresa" : "● Preencher perfil da empresa"}
            </button>
          </div>
        </div>
      </header>

      <div className="corpo">
        <aside className={filtrosAbertos ? "lateral" : "lateral fechada"}>
          {aba === "todas" && (
            <button type="button" className="filtros-toggle" aria-expanded={filtrosAbertos} onClick={() => setFiltrosAbertos((v) => !v)}>
              Filtros {resumoFiltros(filtros)}
              <span aria-hidden>{filtrosAbertos ? "▲" : "▼"}</span>
            </button>
          )}
          {aba === "todas" ? (
            <section className="bloco">
              <h2 className="bloco-titulo">Filtros</h2>
              <fieldset className="grupo">
                <legend>Onde</legend>
                {ondes.map(([valor, rotulo]) => (
                  <label key={valor} className="opcao">
                    <input type="radio" name="abrangencia" checked={filtros.abrangencia === valor} onChange={() => mudarFiltros({ abrangencia: valor })} />
                    {rotulo}
                  </label>
                ))}
                {filtros.abrangencia === "municipio" && (
                  <select id="filtro-municipio" value={filtros.municipio} onChange={(e) => mudarFiltros({ municipio: e.target.value })}>
                    <option value="">Escolha o município</option>
                    {municipiosComAbertas.map((m) => (
                      <option key={m.codigo_ibge} value={m.codigo_ibge}>{m.municipio} ({m.total})</option>
                    ))}
                  </select>
                )}
              </fieldset>
              <fieldset className="grupo">
                <legend>Encerra em até</legend>
                <div className="chips">
                  {prazos.map(([dias, rotulo]) => (
                    <button key={dias} type="button" className={filtros.dias === dias ? "chip ativo" : "chip"} aria-pressed={filtros.dias === dias} onClick={() => mudarFiltros({ dias })}>
                      {rotulo}
                    </button>
                  ))}
                </div>
              </fieldset>
              <fieldset className="grupo">
                <legend>Pequenas empresas</legend>
                <label className="opcao">
                  <input id="filtro-me-epp" type="checkbox" checked={filtros.meEpp} onChange={(e) => mudarFiltros({ meEpp: e.target.checked })} />
                  Só exclusivas para ME/EPP
                </label>
              </fieldset>
            </section>
          ) : (
            <section className="bloco">
              <h2 className="bloco-titulo">Como funciona</h2>
              <p className="texto-lateral">A IA lê o objeto de cada licitação e separa só as que são serviço do seu segmento, dentro da sua faixa de valor.</p>
              {uso && (
                <p className="texto-lateral">
                  <b>{Math.max(0, uso.busca.limite - uso.busca.usados)} de {uso.busca.limite}</b> buscas com IA restantes hoje. A busca por texto na aba “Todas” é livre.
                </p>
              )}
            </section>
          )}

          {perfil && (
            <section className="bloco bloco-perfil">
              <h2 className="bloco-titulo">Seu perfil</h2>
              <dl className="perfil-resumo">
                <dt>Segmento</dt>
                <dd>{capitalizar(perfil.segmento)}</dd>
                <dt>Faixa de valor</dt>
                <dd>{faixa(perfil)}</dd>
                {perfil.nao_faz.length > 0 && (
                  <>
                    <dt>Não faz</dt>
                    <dd>{perfil.nao_faz.join(", ")}</dd>
                  </>
                )}
              </dl>
              <button type="button" className="botao-secundario largo" onClick={abrirPerfil}>Editar perfil</button>
            </section>
          )}

          {status?.banco && (
            <p className="rodape-lateral">
              {status.banco.total.toLocaleString("pt-BR")} editais no banco · atualizado em{" "}
              {new Date(status.banco.ultimo_sync).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}
            </p>
          )}
        </aside>

        <main className="principal">
          <div className="apresentacao">
            <h1>Todas as licitações abertas de {status?.escopo.uf ?? "SP"} num lugar só</h1>
            <p>
              O Radar reúne o que está recebendo proposta no PNCP, o portal oficial de compras públicas. Filtre à vontade e peça
              para a IA ler o edital: ela resume prazo, valor e exigências e diz se vale a pena para a sua empresa.
            </p>
          </div>

          {!perfil && (
            <div className="convite">
              <div>
                <b>Conte o que sua empresa faz</b>
                <p>Sem perfil você vê todas as licitações. Com ele, a IA separa as que servem para você e julga cada edital.</p>
              </div>
              <button type="button" className="botao-primario" onClick={abrirPerfil}>Preencher perfil da empresa</button>
            </div>
          )}

          <div className="principal-topo">
            <div className="abas" role="tablist">
              <button type="button" role="tab" aria-selected={aba === "todas"} className={aba === "todas" ? "aba ativa" : "aba"} onClick={() => abrirAba("todas")}>
                Todas {lista && <span className="contador">{lista.total.toLocaleString("pt-BR")}</span>}
              </button>
              <button type="button" role="tab" aria-selected={aba === "para-voce"} className={aba === "para-voce" ? "aba ativa" : "aba"} onClick={() => abrirAba("para-voce")}>
                ✦ Para você <span className="contador contador-ia">IA</span>
              </button>
            </div>
          </div>

          {erro && <p className="erro">{erro}</p>}

          {aba === "todas" ? (
            <>
              <form className="busca" onSubmit={(e) => { e.preventDefault(); mudarFiltros({ q: textoBusca }); }}>
                <input
                  id="busca-texto"
                  value={textoBusca}
                  onChange={(e) => setTextoBusca(e.target.value)}
                  placeholder="Buscar no objeto: limpeza predial, merenda, impressão…"
                />
                {filtros.q && (
                  <button type="button" className="botao-link" onClick={() => { setTextoBusca(""); mudarFiltros({ q: "" }); }}>limpar</button>
                )}
                <button type="submit" className="botao-primario">Buscar</button>
              </form>

              <div ref={topoLista} className="lista-topo">
                {lista && (
                  <span className="contagem">
                    {lista.total === 0
                      ? "Nenhuma licitação com esses filtros."
                      : <><b>{lista.total.toLocaleString("pt-BR")}</b> licitações · mostrando {((pagina - 1) * POR_PAGINA + 1).toLocaleString("pt-BR")}–{Math.min(pagina * POR_PAGINA, lista.total).toLocaleString("pt-BR")} · {filtros.q ? "mais relevantes primeiro" : "prazo mais próximo primeiro"}</>}
                  </span>
                )}
                {carregandoLista && <span className="carregando-mini"><span className="giro" /> carregando</span>}
              </div>

              {lista && grade(lista.itens)}
              {lista && <Paginacao pagina={pagina} paginas={lista.paginas} onIr={irParaPagina} />}
            </>
          ) : (
            <>
              {!perfil ? (
                <p className="vazio">A aba “Para você” usa o perfil da sua empresa para separar as licitações. Preencha o perfil acima para ver a seleção da IA.</p>
              ) : (
              <>
              <form className="busca" onSubmit={(e) => { e.preventDefault(); procurarComIa(textoIa); }}>
                <input id="busca-ia" value={textoIa} onChange={(e) => setTextoIa(e.target.value)} placeholder="Pergunte para a IA: limpeza hospitalar em Valinhos…" />
                <button type="submit" className="botao-primario" disabled={!textoIa.trim()}>Perguntar</button>
              </form>
              {perfilMudou && !busca && (
                <p className="aviso">Você mudou o perfil. <button type="button" className="botao-link" onClick={() => perfil && carregarFeed(perfil)}>Atualizar a lista</button></p>
              )}

              {busca ? (
                <>
                  <div className="secao-topo">
                    <h2>Resultados para “{busca.pergunta}”</h2>
                    <button type="button" className="botao-link" onClick={() => setBusca(null)}>← voltar</button>
                  </div>
                  {!busca.resultado && !busca.erro && <BarraProgresso inicio={busca.inicio} estimativaS={10} texto="A IA está planejando a busca e separando o que serve para você…" />}
                  {busca.erro && <p className="erro">{busca.erro}</p>}
                  {busca.resultado && <><Contagem itens={busca.resultado.candidatas.length} d={busca.resultado.detalhes} />{grade(busca.resultado.candidatas)}</>}
                </>
              ) : carregandoFeed ? (
                <BarraProgresso inicio={inicioFeed} estimativaS={30} texto="A IA está lendo as licitações da região e do estado…" />
              ) : feed ? (
                <>
                  <div className="secao-topo"><h2>Em {feed.regiao_nome}</h2></div>
                  <Contagem itens={feed.regiao.length} d={feed.detalhes.regiao} />
                  {feed.regiao.length ? grade(ordenarPorPrazo(feed.regiao)) : <p className="vazio">Nada do seu segmento na região agora.</p>}
                  <div className="secao-topo"><h2>No resto de {status?.escopo.uf ?? "SP"}</h2></div>
                  <Contagem itens={feed.estado.length} d={feed.detalhes.estado} />
                  {feed.estado.length ? grade(ordenarPorPrazo(feed.estado)) : <p className="vazio">Nada no resto do estado.</p>}
                </>
              ) : null}
              </>
              )}
            </>
          )}
        </main>
      </div>

      {painelAberto && (
        <>
          <div className="veu" onClick={() => setPainelAberto(false)} />
          <PainelPerfil perfil={rascunho} onMudar={setRascunho} onSalvar={salvarPerfil} onFechar={() => setPainelAberto(false)} />
        </>
      )}

      {tutorial && !painelAberto && (
        <Tutorial alvo={botaoPerfil} onPreencher={abrirPerfil} onFechar={fecharTutorial} />
      )}
    </div>
  );
}

function resumoFiltros(f: FiltrosLista) {
  const ativos = [f.abrangencia !== "estado", f.dias > 0, f.meEpp].filter(Boolean).length;
  return ativos ? `(${ativos} ativo${ativos > 1 ? "s" : ""})` : "";
}

function faixa(p: Perfil) {
  const fmt = (v: number) => (v >= 1_000_000 ? `R$ ${(v / 1_000_000).toLocaleString("pt-BR")} mi` : `R$ ${Math.round(v / 1000)} mil`);
  if (p.faixa_valor_min && p.faixa_valor_max) return `${fmt(p.faixa_valor_min)} a ${fmt(p.faixa_valor_max)}`;
  if (p.faixa_valor_max) return `até ${fmt(p.faixa_valor_max)}`;
  if (p.faixa_valor_min) return `a partir de ${fmt(p.faixa_valor_min)}`;
  return "qualquer valor";
}

function ordenarPorPrazo(itens: Licitacao[]) {
  return [...itens].sort((a, b) => (diasRestantes(a.data_encerramento) ?? 999) - (diasRestantes(b.data_encerramento) ?? 999));
}

function Contagem({ itens, d }: { itens: number; d: ResultadoBusca["detalhes"] }) {
  return (
    <p className="contagem">
      <b>{itens}</b> {itens === 1 ? "serve" : "servem"} para você · a IA descartou {d.descartados_triagem} que citavam seus termos mas são de outro serviço
      {d.fora_da_faixa ? ` · ${d.fora_da_faixa} fora da sua faixa de valor` : ""}
    </p>
  );
}

function Limites({ uso }: { uso: Uso }) {
  const itens = [
    ["resumos", uso.resumo],
    ["buscas com IA", uso.busca],
  ] as const;
  return (
    <span
      className="limites"
      title="Limite diário por pessoa nas ações com IA. Zera à meia-noite. A lista de licitações e a busca por texto são livres."
    >
      Hoje:{" "}
      {itens.map(([nome, c], i) => (
        <span key={nome} className={c.usados >= c.limite ? "limite-esgotado" : ""}>
          {i > 0 && " · "}
          {c.usados}/{c.limite} {nome}
        </span>
      ))}
    </span>
  );
}

function capitalizar(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
