import type { Perfil } from "../tipos";

interface Props {
  perfil: Perfil;
  onMudar: (p: Perfil) => void;
  onSalvar: () => void;
  onFechar: () => void;
}

const lista = (t: string, sep = ",") => t.split(sep).map((x) => x.trim()).filter(Boolean);

export function PainelPerfil({ perfil, onMudar, onSalvar, onFechar }: Props) {
  const campo = <K extends keyof Perfil>(k: K, v: Perfil[K]) => onMudar({ ...perfil, [k]: v });
  const podeSalvar = perfil.segmento.trim().length > 0;

  return (
    <aside className="painel" aria-labelledby="painel-titulo">
      <div className="painel-topo">
        <h2 id="painel-titulo">Perfil da empresa</h2>
        <button type="button" className="fechar" onClick={onFechar} aria-label="Fechar">×</button>
      </div>
      <p className="painel-intro">
        Com estes dados a IA separa as licitações que servem para você e diz, edital por edital, se vale a pena participar.
        Só o segmento é obrigatório.
      </p>

      <label>
        O que sua empresa faz <small>(obrigatório)</small>
        <input value={perfil.segmento} placeholder="ex.: limpeza e conservação predial" onChange={(e) => campo("segmento", e.target.value)} autoFocus />
      </label>
      <label>
        Palavras que aparecem nos editais do seu ramo <small>(separe por vírgula)</small>
        <input
          defaultValue={perfil.palavras_chave.join(", ")}
          placeholder="ex.: limpeza, asseio, zeladoria"
          onBlur={(e) => campo("palavras_chave", lista(e.target.value))}
        />
      </label>
      <div className="dupla">
        <label>
          Valor mínimo (R$)
          <input type="number" value={perfil.faixa_valor_min ?? ""} step={10000} placeholder="ex.: 50000"
            onChange={(e) => campo("faixa_valor_min", e.target.value ? Number(e.target.value) : null)} />
        </label>
        <label>
          Valor máximo (R$)
          <input type="number" value={perfil.faixa_valor_max ?? ""} step={10000} placeholder="ex.: 600000"
            onChange={(e) => campo("faixa_valor_max", e.target.value ? Number(e.target.value) : null)} />
        </label>
      </div>
      <label>
        O que sua empresa não faz <small>(separe por vírgula)</small>
        <input defaultValue={perfil.nao_faz.join(", ")} placeholder="ex.: copeiragem, vigilância" onBlur={(e) => campo("nao_faz", lista(e.target.value))} />
      </label>
      <label>
        Documentos que já tem <small>(um por linha)</small>
        <textarea rows={3} defaultValue={perfil.documentos_que_tem.join("\n")} placeholder={"ex.: certidões fiscais\nbalanço patrimonial"}
          onBlur={(e) => campo("documentos_que_tem", lista(e.target.value, "\n"))} />
      </label>
      <label>
        Nome da empresa <small>(opcional)</small>
        <input value={perfil.nome} onChange={(e) => campo("nome", e.target.value)} />
      </label>

      <button type="button" className="botao-primario" onClick={onSalvar} disabled={!podeSalvar}>Salvar perfil</button>
      <p className="mudo pequeno">{podeSalvar ? "Fica salvo só neste navegador." : "Preencha o que sua empresa faz para salvar."}</p>
    </aside>
  );
}
