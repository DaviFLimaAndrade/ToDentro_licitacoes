import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import { Cartao } from "./componentes/Cartao";
import { Paginacao } from "./componentes/Paginacao";
import { PainelPerfil } from "./componentes/PainelPerfil";
import { Tutorial } from "./componentes/Tutorial";
import { diasRestantes } from "./formato";
import type {
  EstadoAvaliacao, Feed, FiltrosLista, Licitacao, Municipio, PaginaLicitacoes, Perfil, ResultadoBusca, Status, Uso,
} from "./tipos";

const POR_PAGINA = 20;
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
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [perfilSalvo, setPerfilSalvo] = useState(() => guardado.ler<Perfil>("radar.perfil") !== null);
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
  const [busca, setBusca] = useState<{ pergunta: string; resultado?: ResultadoBusca; erro?: string } | null>(null);
  const [textoIa, setTextoIa] = useState("");
  const perfilDoFeed = useRef("");

  const [avaliacoes, setAvaliacoes] = useState<Record<string, EstadoAvaliacao>>({});
  const [abertos, setAbertos] = useState<Set<string>>(new Set());
  const [painelAberto, setPainelAberto] = useState(false);
  const [tutorial, setTutorial] = useState(false);
  const botaoPerfil = useRef<HTMLButtonElement>(null);
  const topoLista = useRef<HTMLDivElement>(null);
  const fila = useRef<Promise<void>>(Promise.resolve());

  useEffect(() => {
    const local = guardado.ler<Perfil>("radar.perfil");
    if (local) setPerfil(local);
    else api.perfil().then(setPerfil).catch((e: Error) => setErro(`Não consegui falar com a API (${e.message}). O uvicorn está rodando?`));
    api.status().then(setStatus).catch(() => setStatus(null));
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
    perfilDoFeed.current = JSON.stringify(p);
    api.feed(p).then(setFeed).catch((e: Error) => setErro(e.message)).finally(() => setCarregandoFeed(false));
  }, []);

  function abrirAba(nova: Aba) {
    setAba(nova);
    if (nova === "para-voce" && perfil && !feed && !carregandoFeed) carregarFeed(perfil);
  }

  function salvarPerfil() {
    if (!perfil) return;
    guardado.gravar("radar.perfil", perfil);
    setPerfilSalvo(true);
    setPainelAberto(false);
    if (feed) carregarFeed(perfil);
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
    if (!perfil) return;
    const p = perfil;
    setAvaliacoes((a) => ({ ...a, [numero]: { estado: "na-fila" } }));
    fila.current = fila.current.then(async () => {
      setAvaliacoes((a) => ({ ...a, [numero]: { estado: "lendo" } }));
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
    setBusca({ pergunta });
    try {
      const resultado = await api.buscar(pergunta, perfil);
      if (resultado.uso) setUso(resultado.uso);
      setBusca({ pergunta, resultado });
    } catch (e) {
      setBusca({ pergunta, erro: (e as Error).message });
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
          onAlternar={() => alternar(l.numero_controle)}
        />
      ))}
    </div>
  );

  const municipiosComAbertas = useMemo(() => municipios.filter((m) => m.total > 0), [municipios]);
  const perfilMudou = perfil !== null && feed !== null && JSON.stringify(perfil) !== perfilDoFeed.current;

  return (
    <div className="pagina">
      <header className="barra-topo">
        <div className="barra-topo-dentro">
          <div className="marca">
            <span className="sobretitulo">Radar de licitações · PNCP</span>
            <strong>{perfil ? capitalizar(perfil.segmento) : "Licitações abertas"}</strong>
          </div>
          <div className="topo-acoes">
            <span className="selo selo-real">Dados reais</span>
          {uso && <Limites uso={uso} />}
            <button
              type="button"
              ref={botaoPerfil}
              className={perfilSalvo ? "botao-secundario" : "botao-vermelho"}
              onClick={() => { setPainelAberto(true); fecharTutorial(); }}
            >
              {perfilSalvo ? "Perfil da empresa" : "● Preencher perfil da empresa"}
            </button>
          </div>
        </div>
      </header>

      <div className="cabecalho">
        <h1>Licitações abertas em {status?.escopo.uf ?? "SP"}</h1>
        {status?.banco && (
          <p className="mudo pequeno">
            {status.banco.total.toLocaleString("pt-BR")} editais recebendo proposta no banco · atualizado em{" "}
            {new Date(status.banco.ultimo_sync).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })} · fonte: PNCP
          </p>
        )}
      </div>

      <div className="abas" role="tablist">
        <button type="button" role="tab" aria-selected={aba === "todas"} className={aba === "todas" ? "aba ativa" : "aba"} onClick={() => abrirAba("todas")}>
          Todas as licitações {lista && <span className="contador">{lista.total.toLocaleString("pt-BR")}</span>}
        </button>
        <button type="button" role="tab" aria-selected={aba === "para-voce"} className={aba === "para-voce" ? "aba ativa" : "aba"} onClick={() => abrirAba("para-voce")}>
          ✦ Para você <span className="contador">IA</span>
        </button>
      </div>

      {erro && <p className="erro">{erro}</p>}

      {aba === "todas" ? (
        <section>
          <form className="busca" onSubmit={(e) => { e.preventDefault(); mudarFiltros({ q: textoBusca }); }}>
            <input
              id="busca-texto"
              value={textoBusca}
              onChange={(e) => setTextoBusca(e.target.value)}
              placeholder="Buscar no objeto, ex.: limpeza predial, merenda, impressão"
            />
            {filtros.q && (
              <button type="button" className="botao-link" onClick={() => { setTextoBusca(""); mudarFiltros({ q: "" }); }}>limpar</button>
            )}
            <button type="submit" className="enviar" aria-label="Buscar">↑</button>
          </form>

          <div className="filtros">
            <select id="filtro-abrangencia" value={filtros.abrangencia} onChange={(e) => mudarFiltros({ abrangencia: e.target.value as FiltrosLista["abrangencia"] })}>
              <option value="estado">Todo o estado de SP</option>
              <option value="regiao">{status?.escopo.regiao ?? "Campinas e região"}</option>
              <option value="municipio">Um município…</option>
            </select>
            {filtros.abrangencia === "municipio" && (
              <select id="filtro-municipio" value={filtros.municipio} onChange={(e) => mudarFiltros({ municipio: e.target.value })}>
                <option value="">Escolha o município</option>
                {municipiosComAbertas.map((m) => (
                  <option key={m.codigo_ibge} value={m.codigo_ibge}>{m.municipio} ({m.total})</option>
                ))}
              </select>
            )}
            <select id="filtro-prazo" value={filtros.dias} onChange={(e) => mudarFiltros({ dias: Number(e.target.value) })}>
              <option value={0}>Qualquer prazo</option>
              <option value={3}>Encerra em até 3 dias</option>
              <option value={7}>Até 7 dias</option>
              <option value={15}>Até 15 dias</option>
              <option value={30}>Até 30 dias</option>
            </select>
            <label className="filtro-check" htmlFor="filtro-me-epp">
              <input id="filtro-me-epp" type="checkbox" checked={filtros.meEpp} onChange={(e) => mudarFiltros({ meEpp: e.target.checked })} />
              Só exclusivas para ME/EPP
            </label>
          </div>
          {filtros.meEpp && status?.banco && status.banco.itens_verificados < status.banco.total && (
            <p className="mudo pequeno">
              Exclusividade verificada em {status.banco.itens_verificados.toLocaleString("pt-BR")} de {status.banco.total.toLocaleString("pt-BR")} licitações até agora
              (os itens de cada compra são baixados aos poucos, começando pela região).
            </p>
          )}

          <div ref={topoLista} className="lista-topo">
            {lista && (
              <span className="mudo pequeno">
                {lista.total === 0
                  ? "Nenhuma licitação com esses filtros."
                  : `Mostrando ${((pagina - 1) * POR_PAGINA + 1).toLocaleString("pt-BR")}–${Math.min(pagina * POR_PAGINA, lista.total).toLocaleString("pt-BR")} de ${lista.total.toLocaleString("pt-BR")} · ${filtros.q ? "mais relevantes primeiro" : "prazo mais próximo primeiro"}`}
              </span>
            )}
            {carregandoLista && <span className="carregando-mini"><span className="giro" /> carregando</span>}
          </div>

          {lista && grade(lista.itens)}
          {lista && <Paginacao pagina={pagina} paginas={lista.paginas} onIr={irParaPagina} />}
        </section>
      ) : (
        <section>
          <p className="mudo">
            A IA lê o objeto de cada licitação e separa só as que são serviço do seu segmento, dentro da sua faixa de valor.
            {!perfilSalvo && <> Para isso funcionar bem, <button type="button" className="botao-link" onClick={() => setPainelAberto(true)}>preencha o perfil da empresa</button>.</>}
          </p>
          {uso && (
            <p className="mudo pequeno">
              Buscas com IA: <b>{Math.max(0, uso.busca.limite - uso.busca.usados)} de {uso.busca.limite}</b> restantes hoje. A busca por texto na aba “Todas” é livre.
            </p>
          )}
          <form className="busca" onSubmit={(e) => { e.preventDefault(); procurarComIa(textoIa); }}>
            <input id="busca-ia" value={textoIa} onChange={(e) => setTextoIa(e.target.value)} placeholder="Pergunte para a IA, ex.: limpeza hospitalar em Valinhos" />
            <button type="submit" className="enviar" disabled={!textoIa.trim()} aria-label="Perguntar">↑</button>
          </form>
          {perfilMudou && !busca && (
            <p className="aviso">Você mudou o perfil. <button type="button" className="botao-link" onClick={() => perfil && carregarFeed(perfil)}>Atualizar</button></p>
          )}

          {busca ? (
            <>
              <div className="secao-topo">
                <h2>Resultados para “{busca.pergunta}”</h2>
                <button type="button" className="botao-link" onClick={() => setBusca(null)}>← voltar</button>
              </div>
              {!busca.resultado && !busca.erro && <Carregando texto="Planejando a busca e fazendo a triagem…" />}
              {busca.erro && <p className="erro">{busca.erro}</p>}
              {busca.resultado && <><Contagem itens={busca.resultado.candidatas.length} d={busca.resultado.detalhes} />{grade(busca.resultado.candidatas)}</>}
            </>
          ) : carregandoFeed ? (
            <Carregando texto="Triando as licitações com IA… (na primeira vez leva uns 30 s)" />
          ) : feed ? (
            <>
              <div className="secao-topo"><h2>Em {feed.regiao_nome}</h2></div>
              <Contagem itens={feed.regiao.length} d={feed.detalhes.regiao} />
              {feed.regiao.length ? grade(ordenarPorPrazo(feed.regiao)) : <p className="mudo vazio">Nada do seu segmento na região agora.</p>}
              <div className="secao-topo"><h2>No resto de {status?.escopo.uf ?? "SP"}</h2></div>
              <Contagem itens={feed.estado.length} d={feed.detalhes.estado} />
              {feed.estado.length ? grade(ordenarPorPrazo(feed.estado)) : <p className="mudo vazio">Nada no resto do estado.</p>}
            </>
          ) : null}
        </section>
      )}

      {painelAberto && perfil && (
        <>
          <div className="veu" onClick={() => setPainelAberto(false)} />
          <PainelPerfil perfil={perfil} onMudar={setPerfil} onSalvar={salvarPerfil} status={status} onFechar={() => setPainelAberto(false)} />
        </>
      )}

      {tutorial && !painelAberto && (
        <Tutorial alvo={botaoPerfil} onPreencher={() => { fecharTutorial(); setPainelAberto(true); }} onFechar={fecharTutorial} />
      )}
    </div>
  );
}

function ordenarPorPrazo(itens: Licitacao[]) {
  return [...itens].sort((a, b) => (diasRestantes(a.data_encerramento) ?? 999) - (diasRestantes(b.data_encerramento) ?? 999));
}

function Contagem({ itens, d }: { itens: number; d: ResultadoBusca["detalhes"] }) {
  return (
    <p className="mudo pequeno">
      {itens} {itens === 1 ? "serve" : "servem"} para você · a IA descartou {d.descartados_triagem} que citavam seus termos mas são de outro serviço
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

function Carregando({ texto }: { texto: string }) {
  return <p className="carregando"><span className="giro" /> {texto}</p>;
}

function capitalizar(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
