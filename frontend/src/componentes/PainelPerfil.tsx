import type { Perfil, Status } from "../tipos";

interface Props {
  perfil: Perfil;
  onMudar: (p: Perfil) => void;
  onSalvar: () => void;
  status: Status | null;
  onFechar: () => void;
}

const lista = (t: string, sep = ",") => t.split(sep).map((x) => x.trim()).filter(Boolean);

export function PainelPerfil({ perfil, onMudar, onSalvar, status, onFechar }: Props) {
  const campo = <K extends keyof Perfil>(k: K, v: Perfil[K]) => onMudar({ ...perfil, [k]: v });

  return (
    <aside className="painel">
      <div className="painel-topo">
        <h2>Perfil da empresa</h2>
        <button type="button" className="fechar" onClick={onFechar} aria-label="Fechar">×</button>
      </div>

      <label>Nome<input value={perfil.nome} onChange={(e) => campo("nome", e.target.value)} /></label>
      <label>Segmento<input value={perfil.segmento} onChange={(e) => campo("segmento", e.target.value)} /></label>
      <label>
        Palavras-chave <small>(separe por vírgula)</small>
        <input
          defaultValue={perfil.palavras_chave.join(", ")}
          onBlur={(e) => campo("palavras_chave", lista(e.target.value))}
        />
      </label>
      <div className="dupla">
        <label>
          Valor mínimo (R$)
          <input type="number" value={perfil.faixa_valor_min ?? ""} step={10000}
            onChange={(e) => campo("faixa_valor_min", e.target.value ? Number(e.target.value) : null)} />
        </label>
        <label>
          Valor máximo (R$)
          <input type="number" value={perfil.faixa_valor_max ?? ""} step={10000}
            onChange={(e) => campo("faixa_valor_max", e.target.value ? Number(e.target.value) : null)} />
        </label>
      </div>
      <label>
        Documentos que tem <small>(um por linha)</small>
        <textarea rows={3} defaultValue={perfil.documentos_que_tem.join("\n")}
          onBlur={(e) => campo("documentos_que_tem", lista(e.target.value, "\n"))} />
      </label>
      <label>
        Não faz <small>(separe por vírgula)</small>
        <input defaultValue={perfil.nao_faz.join(", ")} onBlur={(e) => campo("nao_faz", lista(e.target.value))} />
      </label>
      <button type="button" className="botao-ia" onClick={onSalvar}>Salvar perfil</button>
      <p className="mudo">Fica salvo neste navegador. A aba “Para você” usa estes dados.</p>
      <h2>Banco local</h2>
      {status?.banco ? (
        <p className="mudo">
          {status.banco.total.toLocaleString("pt-BR")} licitações de {status.escopo.uf} · até {status.escopo.dias_max} dias
          <br />
          Último sync: {new Date(status.banco.ultimo_sync).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}
          {status.banco.desatualizado && <><br /><span className="erro">Banco com mais de 1 dia: rode python -m radar.sync</span></>}
        </p>
      ) : (
        <p className="erro">Banco vazio. Rode: python -m radar.sync</p>
      )}
      <p className="mudo">Região de foco: {status?.escopo.regiao} ({status?.escopo.municipios} municípios da RMC)</p>
    </aside>
  );
}
