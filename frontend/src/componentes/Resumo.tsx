import { dataCurta, encurtar, ROTULO, valorCompleto } from "../formato";
import type { Avaliacao, Licitacao, Veredito } from "../tipos";

interface Props {
  licitacao: Licitacao;
  avaliacao: Avaliacao;
  onPedirPerfil: () => void;
}

function QuadroVeredito({ veredito }: { veredito: Veredito }) {
  const tom = veredito.vale_a_pena ? "sim" : veredito.aderencia === "media" ? "talvez" : "nao";
  const titulo = veredito.vale_a_pena ? "Vale a pena participar" : "Provavelmente não vale a pena";
  return (
    <div className={`veredito veredito-${tom}`}>
      <span className="veredito-icone" aria-hidden>{veredito.vale_a_pena ? "✓" : "!"}</span>
      <div>
        <b>{titulo}</b> <span>· {ROTULO[veredito.aderencia].toLowerCase()}</span>
        <p>{veredito.motivo}</p>
        {veredito.bloqueios.length > 0 && (
          <>
            <small>Confirme antes de participar:</small>
            <ul>{veredito.bloqueios.map((b) => <li key={b}>{b}</li>)}</ul>
          </>
        )}
      </div>
    </div>
  );
}

export function Resumo({ licitacao, avaliacao, onPedirPerfil }: Props) {
  const { ficha, veredito } = avaliacao;
  const exigencias = [...ficha.exigencias];
  if (ficha.visita_tecnica) exigencias.push(`Visita técnica: ${ficha.visita_tecnica}`);

  const caixas = [
    ["Prazo da proposta", ficha.prazo_proposta ?? dataCurta(licitacao.data_encerramento)],
    ["Valor estimado", valorCompleto(ficha.valor_estimado ?? licitacao.valor_estimado)],
    ["Modalidade", ficha.modalidade ?? licitacao.modalidade ?? "—"],
    ["Vigência", ficha.vigencia ?? "—"],
  ];

  return (
    <section className="resumo">
      <div className="sobretitulo">Resumo do edital</div>
      <h3>{encurtar(ficha.objeto ?? licitacao.objeto, 160)}</h3>

      <div className="caixas">
        {caixas.map(([rotulo, valor]) => (
          <div className="caixa" key={rotulo}>
            <small>{rotulo}</small>
            <b>{valor}</b>
          </div>
        ))}
      </div>

      <h4>O que você precisa ter</h4>
      {exigencias.length ? (
        <ul>{exigencias.map((e) => <li key={e}>{e}</li>)}</ul>
      ) : (
        <p className="mudo">O edital não lista exigências.</p>
      )}

      {veredito ? (
        <QuadroVeredito veredito={veredito} />
      ) : (
        <div className="veredito veredito-convite">
          <span className="veredito-icone" aria-hidden>?</span>
          <div>
            <b>Vale a pena para a sua empresa?</b>
            <p>Conte o que sua empresa faz e a faixa de valor que atende, e a IA compara com este edital.</p>
            <button type="button" className="botao-primario" onClick={onPedirPerfil}>Preencher perfil da empresa</button>
          </div>
        </div>
      )}

      <p className="fonte">
        Fonte: PNCP · {licitacao.numero_controle} · lido pela IA
        {avaliacao.tempos?.leitor_s !== undefined && (
          <> em {Math.round((avaliacao.tempos.download_s ?? 0) + avaliacao.tempos.leitor_s + (avaliacao.tempos.judge_s ?? 0))} s
            {avaliacao.tempos.cache ? " (do cache)" : avaliacao.tempos.modo === "pdf" ? " (PDF escaneado)" : ""}</>
        )}
        {avaliacao.url_edital && <> · <a href={avaliacao.url_edital} target="_blank" rel="noreferrer">abrir edital completo</a></>}
        {licitacao.link_sistema_origem && <> · <a href={licitacao.link_sistema_origem} target="_blank" rel="noreferrer">onde participar</a></>}
      </p>
      {ficha.trecho_fonte && <p className="fonte">Trecho do edital: “{encurtar(ficha.trecho_fonte, 220)}”</p>}
    </section>
  );
}
