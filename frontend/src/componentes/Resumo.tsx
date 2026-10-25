import { dataCurta, encurtar, ROTULO, valorCompleto } from "../formato";
import type { Avaliacao, Licitacao } from "../tipos";

export function Resumo({ licitacao, avaliacao }: { licitacao: Licitacao; avaliacao: Avaliacao }) {
  const { ficha, veredito } = avaliacao;
  const exigencias = [...ficha.exigencias];
  if (ficha.visita_tecnica) exigencias.push(`Visita técnica: ${ficha.visita_tecnica}`);

  const tom = veredito.vale_a_pena ? "sim" : veredito.aderencia === "media" ? "talvez" : "nao";
  const titulo = veredito.vale_a_pena ? "Vale a pena participar" : "Provavelmente não vale a pena";

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

      <div className={`veredito veredito-${tom}`}>
        <span className="veredito-icone" aria-hidden>{veredito.vale_a_pena ? "✓" : "!"}</span>
        <div>
          <b>{titulo}</b> <span className="mudo">· {ROTULO[veredito.aderencia].toLowerCase()}</span>
          <p>{veredito.motivo}</p>
          {veredito.bloqueios.length > 0 && (
            <>
              <small>Confirme antes de participar:</small>
              <ul>{veredito.bloqueios.map((b) => <li key={b}>{b}</li>)}</ul>
            </>
          )}
        </div>
      </div>

      <p className="fonte">
        Fonte: PNCP · {licitacao.numero_controle} · lido pelo agente leitor
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
