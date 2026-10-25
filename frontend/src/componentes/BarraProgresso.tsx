import { useEffect, useState } from "react";

interface Props {
  inicio: number;
  estimativaS: number;
  texto: string;
  estimativaLongaS?: number;
  textoLongo?: string;
}

function progresso(decorrido: number, estimativa: number): number {
  if (decorrido <= estimativa) return (decorrido / estimativa) * 0.9;
  return 0.9 + 0.08 * (1 - Math.exp(-(decorrido - estimativa) / estimativa));
}

export function BarraProgresso({ inicio, estimativaS, texto, estimativaLongaS, textoLongo }: Props) {
  const [agora, setAgora] = useState(() => Date.now());

  useEffect(() => {
    const id = window.setInterval(() => setAgora(Date.now()), 250);
    return () => window.clearInterval(id);
  }, []);

  const decorrido = (agora - inicio) / 1000;
  const longo = estimativaLongaS !== undefined && decorrido > estimativaS;
  const estimativa = longo ? estimativaLongaS : estimativaS;
  const fracao = progresso(decorrido, estimativa);
  const restante = Math.max(0, Math.ceil(estimativa - decorrido));

  return (
    <div className="progresso" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(fracao * 100)} aria-label={texto}>
      <div className="progresso-linha">
        <span>{longo && textoLongo ? textoLongo : texto}</span>
        <span className="progresso-tempo">{restante > 0 ? `~${restante} s restantes` : "quase pronto…"}</span>
      </div>
      <div className="progresso-trilho">
        <div className="progresso-barra" style={{ width: `${Math.round(fracao * 100)}%` }} />
      </div>
    </div>
  );
}
