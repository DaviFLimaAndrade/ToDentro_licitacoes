# Avaliação da triagem (perfil: limpeza predial)

Gerado em 24/10/2026 23:51. Rótulos tirados dos itens da compra no PNCP (material/serviço e descrição do catálogo); casos ambíguos revisados por IA (não por humano), com motivo. A triagem só vê o texto do objeto.

| Métrica | Valor |
| --- | --- |
| Licitações no conjunto | 61 |
| Avaliáveis (rótulo serve/não serve) | 61 |
| **Precisão** (das que a IA mostrou, quantas servem) | **87%** |
| **Recall** (das que servem, quantas a IA mostrou) | **95%** |
| Acurácia | 93% |
| Matriz | VP 20 · FP 3 · FN 1 · VN 37 |
| Ambíguos sem revisão / sem dados | 0 / 0 |

## Erros da triagem

- **deixou passar** · Guararema · Contratação de empresa para prestação de serviços de limpeza, asseio, conservação predial, incluindo algumas funções de copa e limpeza de vi — rótulo: limpeza predial é o principal; 'algumas funções de copa' são acessórias, não um serviço de copeiragem
- **mostrou sem servir** · Tupã · SERVIÇO DE HIGIENIZAÇÃO, LIMPEZA E DESINFECÇÃO DOS RESERVATÓRIOS E CISTERNAS DE ÁGUA DA UNIDADE — rótulo: limpeza de reservatórios e cisternas: serviço hidráulico/sanitário, outro ramo; IA: Higienização e limpeza de reservatórios de água
- **mostrou sem servir** · São Paulo · serviço de higienização, limpeza e desinfecção de caixas e reservatórios d’água da PRIP/USP, localizados na Cidade Universitária Butantã, Sã — rótulo: limpeza de caixas e reservatórios d'água: outro ramo; IA: Higienização e limpeza de caixas d'água
- **mostrou sem servir** · São Paulo · Contratação de empresa especializada em serviços contínuos de limpeza, higienização e desinfecção de reservatórios e caixas de água para o C — rótulo: limpeza de reservatórios e caixas d'água: outro ramo; IA: Limpeza e desinfecção de reservatórios de água
