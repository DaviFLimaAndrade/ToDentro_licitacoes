import { type RefObject, useEffect, useLayoutEffect, useState } from "react";

interface Props {
  alvo: RefObject<HTMLElement | null>;
  onPreencher: () => void;
  onFechar: () => void;
}

const FOLGA = 8;

export function Tutorial({ alvo, onPreencher, onFechar }: Props) {
  const [rect, setRect] = useState<DOMRect | null>(null);

  useLayoutEffect(() => {
    const medir = () => setRect(alvo.current?.getBoundingClientRect() ?? null);
    medir();
    window.addEventListener("resize", medir);
    window.addEventListener("scroll", medir, { passive: true });
    return () => {
      window.removeEventListener("resize", medir);
      window.removeEventListener("scroll", medir);
    };
  }, [alvo]);

  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onFechar();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onFechar]);

  if (!rect) return null;
  const luz = { top: rect.top - FOLGA, left: rect.left - FOLGA, width: rect.width + 2 * FOLGA, height: rect.height + 2 * FOLGA };
  const largura = Math.min(340, window.innerWidth - 32);
  const esquerda = Math.max(16, Math.min(rect.right - largura, window.innerWidth - largura - 16));

  return (
    <div className="tutorial" role="dialog" aria-modal="true" aria-labelledby="tutorial-titulo">
      <div className="tutorial-luz" style={luz} />
      <div className="tutorial-balao" style={{ top: luz.top + luz.height + 14, left: esquerda, width: largura }}>
        <span className="tutorial-passo">Antes de olhar as licitações</span>
        <h2 id="tutorial-titulo">Conte sobre a sua empresa</h2>
        <p>
          Com o seu segmento, a faixa de valor que você atende e o que você <strong>não</strong> faz, a IA separa só as
          licitações que servem para você e diz, edital por edital, se vale a pena participar.
        </p>
        <div className="tutorial-acoes">
          <button type="button" className="botao-vermelho" onClick={onPreencher} autoFocus>Preencher dados da empresa</button>
          <button type="button" className="botao-link" onClick={onFechar}>Agora não</button>
        </div>
      </div>
    </div>
  );
}
