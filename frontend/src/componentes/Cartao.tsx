import { dataCurta, diasRestantes, encurtar, linkPncp, ROTULO, valorCurto } from "../formato";
import type { EstadoAvaliacao, Licitacao } from "../tipos";
import { BarraProgresso } from "./BarraProgresso";
import { Resumo } from "./Resumo";

interface Props {
  licitacao: Licitacao;
  avaliacao?: EstadoAvaliacao;
  aberto: boolean;
  onResumir: () => void;
  onAlternar: () => void;
  resumosRestantes: number | null;
  onPedirPerfil: () => void;
}

function Selo({ avaliacao, triada }: { avaliacao?: EstadoAvaliacao; triada: boolean }) {
  if (avaliacao?.estado === "ok") {
    const v = avaliacao.dados.veredito;
    if (!v) return <span className="selo selo-neutro">Edital lido</span>;
    return <span className={`selo selo-${v.aderencia}`}>{ROTULO[v.aderencia]}</span>;
  }
  return triada ? <span className="selo selo-neutro">Passou na triagem</span> : <span />;
}

function Prazo({ iso }: { iso?: string }) {
  const dias = diasRestantes(iso);
  const nivel = dias === null ? "" : dias <= 3 ? "prazo-urgente" : dias <= 7 ? "prazo-alerta" : "";
  const quando = dias === null ? "" : dias <= 0 ? "encerra hoje" : `${dias} dia${dias === 1 ? "" : "s"}`;
  return (
    <span className={`prazo ${nivel}`} title="Prazo para enviar a proposta">
      <b>{quando}</b>
      <span>{dataCurta(iso)}</span>
    </span>
  );
}

function Acao({ avaliacao, aberto, onResumir, onAlternar, resumosRestantes }: Omit<Props, "licitacao">) {
  switch (avaliacao?.estado) {
    case "lendo":
      return (
        <BarraProgresso
          inicio={avaliacao.inicio}
          estimativaS={12}
          texto="Lendo o edital…"
          estimativaLongaS={75}
          textoLongo="Edital grande (provavelmente escaneado), lendo as páginas…"
        />
      );
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
          {resumosRestantes !== null && <span className="restantes">{resumosRestantes} restantes hoje</span>}
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
      <dl className="meta">
        <div>
          <dt>Local</dt>
          <dd>{licitacao.municipio}/{licitacao.uf}</dd>
        </div>
        <div>
          <dt>Valor</dt>
          <dd>{valorCurto(licitacao.valor_estimado)}</dd>
        </div>
        <div className="meta-largo">
          <dt>Órgão</dt>
          <dd>{licitacao.orgao}</dd>
        </div>
        <div className="meta-largo">
          <dt>Modalidade</dt>
          <dd>{licitacao.modalidade}</dd>
        </div>
      </dl>
      {licitacao.motivo_triagem && <p className="triagem"><b>Triagem da IA:</b> {licitacao.motivo_triagem}</p>}
      <div className="acoes">
        <Acao {...props} />
        {pncp && <a className="link-pncp" href={pncp} target="_blank" rel="noreferrer">ver no PNCP ↗</a>}
      </div>
      {aberto && avaliacao?.estado === "ok" && <Resumo licitacao={licitacao} avaliacao={avaliacao.dados} onPedirPerfil={props.onPedirPerfil} />}
    </article>
  );
}
