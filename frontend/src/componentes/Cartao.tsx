import { dataCurta, diasRestantes, encurtar, linkPncp, ROTULO, valorCurto } from "../formato";
import type { EstadoAvaliacao, Licitacao } from "../tipos";
import { Resumo } from "./Resumo";

interface Props {
  licitacao: Licitacao;
  avaliacao?: EstadoAvaliacao;
  aberto: boolean;
  onResumir: () => void;
  onAlternar: () => void;
  resumosRestantes: number | null;
}

function Selo({ avaliacao, triada }: { avaliacao?: EstadoAvaliacao; triada: boolean }) {
  if (avaliacao?.estado === "ok") {
    const a = avaliacao.dados.veredito.aderencia;
    return <span className={`selo selo-${a}`}>{ROTULO[a]}</span>;
  }
  return triada ? <span className="selo selo-neutro">Passou na triagem</span> : <span />;
}

function Prazo({ iso }: { iso?: string }) {
  const dias = diasRestantes(iso);
  const urgente = dias !== null && dias >= 0 && dias <= 3;
  const texto =
    dias === null ? dataCurta(iso) : dias <= 0 ? "encerra hoje" : `${dataCurta(iso)} · ${dias} dia${dias === 1 ? "" : "s"}`;
  return <span className={`prazo ${urgente ? "prazo-urgente" : ""}`}>⏰ {texto}</span>;
}

function Acao({ avaliacao, aberto, onResumir, onAlternar, resumosRestantes }: Omit<Props, "licitacao">) {
  switch (avaliacao?.estado) {
    case "lendo":
      return <span className="lendo"><span className="giro" /> Lendo o edital e julgando… (~10 s; escaneado, ~1 min)</span>;
    case "na-fila":
      return <span className="lendo">Na fila para leitura…</span>;
    case "ok":
      return (
        <button type="button" className="botao-secundario" onClick={onAlternar}>
          {aberto ? "Ocultar resumo" : "Ver resumo"}
        </button>
      );
    case "erro":
      return (
        <>
          <span className="erro">{encurtar(avaliacao.erro, 140)}</span>
          <button type="button" className="botao-secundario" onClick={onResumir}>Tentar de novo</button>
        </>
      );
    default:
      if (resumosRestantes !== null && resumosRestantes <= 0) {
        return <span className="mudo pequeno">Limite de resumos de hoje atingido. Volta à meia-noite.</span>;
      }
      return (
        <>
          <button type="button" className="botao-ia" onClick={onResumir}>✦ Resumir edital com IA</button>
          {resumosRestantes !== null && <span className="mudo pequeno">{resumosRestantes} restantes hoje</span>}
        </>
      );
  }
}

export function Cartao(props: Props) {
  const { licitacao, avaliacao, aberto } = props;
  const pncp = linkPncp(licitacao.numero_controle);
  return (
    <article className={`cartao ${aberto ? "cartao-aberto" : ""}`}>
      <div className="cartao-topo">
        <div className="selos">
          <Selo avaliacao={avaliacao} triada={Boolean(licitacao.motivo_triagem)} />
          {licitacao.me_epp === "exclusiva" && (
            <span className="selo selo-me-epp" title="Só micro e pequenas empresas podem participar">Exclusiva ME/EPP</span>
          )}
          {licitacao.me_epp === "parcial" && (
            <span className="selo selo-me-epp-parcial" title="Parte dos itens tem cota ou benefício para ME/EPP">Cota ME/EPP</span>
          )}
        </div>
        <Prazo iso={licitacao.data_encerramento} />
      </div>
      <h3 className="objeto">{encurtar(licitacao.objeto, 150)}</h3>
      <div className="local">{licitacao.municipio}/{licitacao.uf}</div>
      <div className="meta">
        <span>{licitacao.orgao}</span>
        <span>{licitacao.modalidade}</span>
        <span>{valorCurto(licitacao.valor_estimado)}</span>
      </div>
      {licitacao.motivo_triagem && <div className="triagem">Triagem da IA: {licitacao.motivo_triagem}</div>}
      <div className="acoes">
        <Acao {...props} />
        {pncp && <a className="link-pncp" href={pncp} target="_blank" rel="noreferrer">ver no PNCP ↗</a>}
      </div>
      {aberto && avaliacao?.estado === "ok" && <Resumo licitacao={licitacao} avaliacao={avaliacao.dados} />}
    </article>
  );
}
