'use client';

import dynamic from 'next/dynamic';
import { Network } from 'lucide-react';

const StrategiesBuilder = dynamic(() => import('@/components/StrategiesBuilder'), {
  ssr: false,
  loading: () => (
    <div className="card flex items-center justify-center" style={{ height: 600 }}>
      <span className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin"
        style={{ borderColor: 'var(--dw-rule)', borderTopColor: 'var(--dw-blue)' }} />
    </div>
  ),
});

export default function EstrategiasPage() {
  return (
    <div className="main-content">
      {/* Header */}
      <div className="page-header">
        <div>
          <div className="label mb-2 flex items-center gap-2">
            <Network className="w-4 h-4" />
            Operações Estruturadas
          </div>
          <h1 className="font-serif">Estratégias de Opções</h1>
          <p className="mt-2 text-dw-ink-light text-base max-w-2xl">
            Simule, construa e analise estratégias com múltiplas pernas (Straddle, Spreads, Iron Condor). 
            Visualize o payoff de expiração e o impacto das gregas na posição agregada.
          </p>
        </div>
      </div>

      {/* Main Builder Component */}
      <StrategiesBuilder />

      {/* Documentation / Info Card */}
      <div className="card mt-6">
        <h3 className="font-serif text-lg text-dw-ink mb-4">Guia Rápido de Estratégias</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm text-dw-ink-mid leading-relaxed">
          {/* Coluna 1: Posições Puras e Com Ação */}
          <div>
            <div className="mb-8">
              <h4 className="font-bold text-dw-blue mb-4 text-lg border-b-2 border-dw-rule pb-2 flex items-center gap-2">
                <span>📌</span> Posições Puras
              </h4>
              
              <h5 className="font-bold text-dw-ink mt-3 mb-1 flex items-center flex-wrap gap-2">
                Long Call <span className="font-normal text-dw-ink-muted text-sm">(Compra de Call)</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-emerald-600 bg-emerald-50 border-emerald-200">alta</span>
                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border text-red-700 bg-red-50 border-red-200">Débito (Pagando)</span>
              </h5>
              <p className="mb-1">Aposta direcional de alta. Risco limitado ao prêmio pago pela opção, com potencial de ganho ilimitado caso o ativo suba.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> Comprar Call de PETR4 strike R$35,00 quando a ação está R$34,00, esperando uma forte alta após o resultado trimestral.
              </div>
              
              <h5 className="font-bold text-dw-ink mb-1 flex items-center flex-wrap gap-2">
                Short Call <span className="font-normal text-dw-ink-muted text-sm">(Venda de Call)</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-blue-600 bg-blue-50 border-blue-200">neutro</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-red-600 bg-white border-red-200">⚠</span>
                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border text-green-700 bg-green-50 border-green-200">Crédito (Recebendo)</span>
              </h5>
              <p className="mb-1">Gera renda acreditando na lateralização ou queda do ativo. Carrega risco ilimitado se o ativo subir fortemente.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> Vender Call de VALE3 strike R$70,00 (recebendo taxa), apostando que a ação não terá forças para ultrapassar esse valor.
              </div>
              
              <h5 className="font-bold text-dw-ink mb-1 flex items-center flex-wrap gap-2">
                Long Put <span className="font-normal text-dw-ink-muted text-sm">(Compra de Put)</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-rose-600 bg-rose-50 border-rose-200">baixa</span>
                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border text-red-700 bg-red-50 border-red-200">Débito (Pagando)</span>
              </h5>
              <p className="mb-1">Aposta direcional de baixa. Risco limitado ao prêmio pago, lucrando com a desvalorização do ativo.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> Comprar Put de BOVA11 strike R$130,00 apostando em uma queda forte do Ibovespa devido a uma crise macroeconômica.
              </div>
              
              <h5 className="font-bold text-dw-ink mb-1 flex items-center flex-wrap gap-2">
                Short Put <span className="font-normal text-dw-ink-muted text-sm">(Venda de Put)</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-emerald-600 bg-emerald-50 border-emerald-200">alta</span>
                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border text-green-700 bg-green-50 border-green-200">Crédito (Recebendo)</span>
              </h5>
              <p className="mb-1">Gera renda ou serve para comprar o ativo mais barato. Lucra com estabilidade ou alta, mas assume a obrigação de comprar o ativo se cair.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> Vender Put de ITUB4 strike R$30,00 quando ela está R$32,00. Se cair abaixo de R$30, você é obrigado a comprar o papel com "desconto". Se subir, embolsa o prêmio.
              </div>
            </div>

            <div className="mb-8">
              <h4 className="font-bold text-dw-blue mb-4 text-lg border-b-2 border-dw-rule pb-2 flex items-center gap-2">
                <span>🏢</span> Com Ação (Stock)
              </h4>
              
              <h5 className="font-bold text-dw-ink mt-3 mb-1 flex items-center flex-wrap gap-2">
                Covered Call <span className="font-normal text-dw-ink-muted text-sm">(Venda Coberta)</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-amber-600 bg-amber-50 border-amber-200">renda</span>
                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border text-green-700 bg-green-50 border-green-200">Crédito (Recebendo)</span>
              </h5>
              <p className="mb-1">Rentabiliza uma carteira de ações através da venda de Calls. Protege levemente contra quedas, mas limita o ganho máximo na alta.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> Você tem 1.000 ações BBAS3 a R$28,00 e vende 1.000 Calls strike R$30,00. Você recebe uma taxa, mas se a ação for a R$35,00, terá que entregar tudo a R$30,00.
              </div>
              
              <h5 className="font-bold text-dw-ink mb-1 flex items-center flex-wrap gap-2">
                Protective Put <span className="font-normal text-dw-ink-muted text-sm">(Put Protetora)</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-purple-600 bg-purple-50 border-purple-200">hedge</span>
                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border text-red-700 bg-red-50 border-red-200">Débito (Pagando)</span>
              </h5>
              <p className="mb-1">Funciona como um seguro para quem possui a ação. Limita o risco de baixa preservando o potencial de alta, ao custo do prêmio da opção.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> Comprar WEGE3 a R$50,00 e comprar a Put de strike R$48,00 junto. Se a ação despencar para R$30,00, você tem o direito garantido de sair a R$48,00.
              </div>
            </div>
            
            <div className="mb-8">
              <h4 className="font-bold text-dw-blue mb-4 text-lg border-b-2 border-dw-rule pb-2 flex items-center gap-2">
                <span>📊</span> Spreads (Travas)
              </h4>
              
              <h5 className="font-bold text-dw-ink mt-3 mb-1 flex items-center flex-wrap gap-2">
                Bull Call Spread <span className="font-normal text-dw-ink-muted text-sm">(Trava de Alta com Call)</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-emerald-600 bg-emerald-50 border-emerald-200">alta</span>
                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border text-red-700 bg-red-50 border-red-200">Débito (Pagando)</span>
              </h5>
              <p className="mb-1">Aposta direcional de alta com risco limitado. Compra-se uma Call mais próxima do dinheiro e vende-se uma Call mais fora do dinheiro para reduzir o custo.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> BBDC4 a R$14,00. Você compra Call R$14,00 e vende a Call R$15,00. Operação bem mais barata que a compra seca, mirando alvo até R$15,00.
              </div>
              
              <h5 className="font-bold text-dw-ink mb-1 flex items-center flex-wrap gap-2">
                Bear Put Spread <span className="font-normal text-dw-ink-muted text-sm">(Trava de Baixa com Put)</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-rose-600 bg-rose-50 border-rose-200">baixa</span>
                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border text-red-700 bg-red-50 border-red-200">Débito (Pagando)</span>
              </h5>
              <p className="mb-1">Aposta direcional de baixa. Compra-se uma Put e vende-se uma Put com strike menor. Também reduz o custo da operação limitando o lucro máximo.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> B3SA3 a R$11,00. Compra Put R$11,00 e vende Put R$10,00. Paga menos na aposta de que o ativo recuará até os R$10,00.
              </div>
            </div>
          </div>

          {/* Coluna 2: Spreads de Crédito, Volatilidade e Complexas */}
          <div>
            <div className="mb-8">
              <h4 className="font-bold text-dw-blue mb-4 text-lg border-b-2 border-dw-rule pb-2 flex items-center gap-2 invisible hidden md:flex">
                <span>📊</span> Spreads (Continuação)
              </h4>
              
              <h5 className="font-bold text-dw-ink mt-3 mb-1 flex items-center flex-wrap gap-2">
                Bull Put Spread <span className="font-normal text-dw-ink-muted text-sm">(Trava de Alta com Put)</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-amber-600 bg-amber-50 border-amber-200">renda</span>
                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border text-green-700 bg-green-50 border-green-200">Crédito (Recebendo)</span>
              </h5>
              <p className="mb-1">Trava de alta recebendo crédito. Aposta-se que o ativo não vai cair abaixo do strike vendido. Lucra com alta, estabilidade ou leve queda.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> RENT3 a R$40,00. Você vende Put R$38,00 e compra Put R$36,00. Recebe dinheiro na conta e lucra o máximo se a ação não cair de R$38,00 até o vencimento.
              </div>
              
              <h5 className="font-bold text-dw-ink mb-1 flex items-center flex-wrap gap-2">
                Bear Call Spread <span className="font-normal text-dw-ink-muted text-sm">(Trava de Baixa com Call)</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-amber-600 bg-amber-50 border-amber-200">renda</span>
                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border text-green-700 bg-green-50 border-green-200">Crédito (Recebendo)</span>
              </h5>
              <p className="mb-1">Trava de baixa recebendo crédito. Aposta-se que o ativo não vai subir acima do strike vendido. Lucra com baixa, estabilidade ou leve alta.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> ABEV3 a R$12,00. Você vende Call R$13,00 e compra Call R$14,00. Fica com o prêmio caso o ativo sofra resistência e não passe de R$13,00.
              </div>
            </div>

            <div className="mb-8">
              <h4 className="font-bold text-dw-blue mb-4 text-lg border-b-2 border-dw-rule pb-2 flex items-center gap-2">
                <span>🌊</span> Volatilidade
              </h4>
              
              <h5 className="font-bold text-dw-ink mt-3 mb-1 flex items-center flex-wrap gap-2">
                Long Straddle <span className="font-normal text-dw-ink-muted text-sm">(Straddle Comprado)</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-blue-600 bg-blue-50 border-blue-200">neutro</span>
                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border text-red-700 bg-red-50 border-red-200">Débito (Pagando)</span>
              </h5>
              <p className="mb-1">Estratégias de compra de volatilidade. Você compra uma Call e uma Put. Lucra se o ativo se mover fortemente para qualquer direção.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> Prévia do balanço da PETR4 (incerteza alta). Compra Call R$36 e Put R$36. O que importa é um movimento explosivo para R$40 (lucro na Call) ou R$32 (lucro na Put).
              </div>

              <h5 className="font-bold text-dw-ink mt-3 mb-1 flex items-center flex-wrap gap-2">
                Long Strangle <span className="font-normal text-dw-ink-muted text-sm">(Strangle Comprado)</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-blue-600 bg-blue-50 border-blue-200">neutro</span>
                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border text-red-700 bg-red-50 border-red-200">Débito (Pagando)</span>
              </h5>
              <p className="mb-1">Semelhante ao Straddle Comprado, mas utilizando opções Fora do Dinheiro (OTM). É mais barato de montar, porém exige um movimento mais expressivo para dar lucro.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> PETR4 a R$35,00. Compra Call R$37 e Put R$33. Paga mais barato mas precisa que rompa forte para cima ou para baixo.
              </div>
              
              <h5 className="font-bold text-dw-ink mb-1 flex items-center flex-wrap gap-2">
                Short Straddle <span className="font-normal text-dw-ink-muted text-sm">(Straddle Vendido)</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-amber-600 bg-amber-50 border-amber-200">renda</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-red-600 bg-white border-red-200">⚠</span>
                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border text-green-700 bg-green-50 border-green-200">Crédito (Recebendo)</span>
              </h5>
              <p className="mb-1">Aposta na lateralização e queda de volatilidade. Vende-se Call e Put no mesmo strike. Gera renda alta, mas carrega risco ilimitado em fortes movimentos.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> MGLU3 parada em R$4,50. Vende-se Call e Put no strike R$4,50. O ideal é o ativo expirar exatamente nesse miolo para derreter o prêmio (Theta) a seu favor.
              </div>

              <h5 className="font-bold text-dw-ink mb-1 flex items-center flex-wrap gap-2">
                Short Strangle <span className="font-normal text-dw-ink-muted text-sm">(Strangle Vendido)</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-amber-600 bg-amber-50 border-amber-200">renda</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-red-600 bg-white border-red-200">⚠</span>
                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border text-green-700 bg-green-50 border-green-200">Crédito (Recebendo)</span>
              </h5>
              <p className="mb-1">Aposta na lateralização, mas com uma margem de segurança maior que o Straddle (vende opções OTM). Recebe um prêmio menor, mas o ativo tem espaço para oscilar sem dar prejuízo.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> BOVA11 a R$130. Vende Call R$135 e Put R$125. Você ganha se o índice ficar dançando apenas dentro dessa faixa até o vencimento.
              </div>
              
              <h5 className="font-bold text-dw-ink mb-1 flex items-center flex-wrap gap-2">
                Butterfly Spread <span className="font-normal text-dw-ink-muted text-sm">(Borboleta)</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-blue-600 bg-blue-50 border-blue-200">neutro</span>
                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border text-red-700 bg-red-50 border-red-200">Débito (Pagando)</span>
              </h5>
              <p className="mb-1">Aposta em alvo específico e estabilidade. O lucro máximo ocorre se o ativo expirar exatamente no strike central (venda de 2 opções).</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> VALE3 a R$60,00, sem sinal de tendência. Você compra Call R$58, vende 2x Call R$60 e compra Call R$62. O lucro explode caso o papel estacione exatamente nos R$60 no vencimento.
              </div>
            </div>

            <div className="mb-8">
              <h4 className="font-bold text-dw-blue mb-4 text-lg border-b-2 border-dw-rule pb-2 flex items-center gap-2">
                <span>🦅</span> Estratégias Complexas
              </h4>
              
              <h5 className="font-bold text-dw-ink mt-3 mb-1 flex items-center flex-wrap gap-2">
                Iron Condor
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border text-amber-600 bg-amber-50 border-amber-200">renda</span>
                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border text-green-700 bg-green-50 border-green-200">Crédito (Recebendo)</span>
              </h5>
              <p className="mb-1">Estratégia não-direcional de venda de volatilidade. Formada por um Bull Put Spread e um Bear Call Spread (4 pernas OTM). Lucra em mercado lateral.</p>
              <div className="mb-4 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> BOVA11 rondando entre R$125 e R$135. Você monta um Bull Put R$120/125 (trava embaixo) e um Bear Call R$135/140 (trava em cima). Lucro máximo se BOVA11 fechar entre R$125 e R$135.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Documentação — Estratégias Avançadas (novas categorias) */}
      <div className="card mt-6">
        <h3 className="font-serif text-lg text-dw-ink mb-4">Estratégias Avançadas</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm text-dw-ink-mid leading-relaxed">

          {/* Coluna 1 */}
          <div>
            <div className="mb-8">
              <h4 className="font-bold text-dw-blue mb-4 text-lg border-b-2 border-dw-rule pb-2 flex items-center gap-2">
                <span>⚖️</span> Razão / Backspread
              </h4>
              <p className="mb-1"><strong>Call Ratio Backspread</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-emerald-600 bg-emerald-50 border-emerald-200">alta</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-green-700 bg-green-50 border-green-200">Crédito (Recebendo)</span> — vende 1 call e compra 2 acima (geralmente crédito). Viés de alta forte + long vol; lucro ilimitado p/ cima, perda limitada no strike das compradas.</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> PETR4 a R$36 — vende 1 call R$36 e compra 2 calls R$40, por crédito, mirando uma alta explosiva pós-balanço.
              </div>
              <p className="mb-1"><strong>Put Ratio Backspread</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-rose-600 bg-rose-50 border-rose-200">baixa</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-green-700 bg-green-50 border-green-200">Crédito (Recebendo)</span> — compra 2 puts e vende 1 acima. Baixa forte + long vol; grande lucro na queda.</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> VALE3 a R$58 — compra 2 puts R$54 e vende 1 put R$58 (crédito), apostando em queda forte com proteção se o papel subir.
              </div>
              <p className="mb-1"><strong>Call Front Ratio Spread</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-amber-600 bg-amber-50 border-amber-200">renda</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-green-700 bg-green-50 border-green-200">Crédito (Recebendo)</span> — compra 1 call e vende 2 acima. Neutro/leve alta, short vol; <strong>risco ilimitado</strong> p/ cima (call a descoberto).</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> ABEV3 a R$12 — compra 1 call R$12 e vende 2 calls R$13, recebendo prêmio; lucro máximo nos R$13, mas risco se disparar.
              </div>
              <p className="mb-1"><strong>Put Front Ratio Spread</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-amber-600 bg-amber-50 border-amber-200">renda</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-green-700 bg-green-50 border-green-200">Crédito (Recebendo)</span> — compra 1 put e vende 2 abaixo. Neutro/leve baixa, short vol; risco grande p/ baixo.</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> BBDC4 a R$14 — compra 1 put R$14 e vende 2 puts R$13 (crédito); ganho máximo se fechar nos R$13.
              </div>
            </div>

            <div className="mb-8">
              <h4 className="font-bold text-dw-blue mb-4 text-lg border-b-2 border-dw-rule pb-2 flex items-center gap-2">
                <span>🦋</span> Borboletas &amp; Condores Avançados
              </h4>
              <p className="mb-1"><strong>Iron Butterfly</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-amber-600 bg-amber-50 border-amber-200">renda</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-green-700 bg-green-50 border-green-200">Crédito (Recebendo)</span> — vende straddle ATM e compra as asas (put OTM + call OTM). Neutro, short vol; lucro máximo no strike central.</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> VALE3 a R$60 — vende call e put R$60 (ATM) e compra put R$56 + call R$64. Lucro máximo se expirar nos R$60.
              </div>
              <p className="mb-1"><strong>Long Condor</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-blue-600 bg-blue-50 border-blue-200">neutro</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-red-700 bg-red-50 border-red-200">Débito (Pagando)</span> — compra as pontas e vende o miolo (mesmo tipo). Neutro; lucro num intervalo amplo, risco = débito.</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> BOVA11 a R$130 — compra call R$120, vende R$127 e R$133, compra R$140. Lucra com o índice entre R$127 e R$133.
              </div>
              <p className="mb-1"><strong>Broken Wing Butterfly</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-blue-600 bg-blue-50 border-blue-200">neutro</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-slate-700 bg-slate-100 border-slate-300">Misto</span> — borboleta com asas de larguras diferentes; pode zerar o risco de um lado se montada por crédito.</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> PETR4 a R$36 — compra call R$36, vende 2x call R$38 e compra call R$42 (asa direita mais larga), por crédito, anulando o risco de baixa.
              </div>
            </div>

            <div className="mb-8">
              <h4 className="font-bold text-dw-blue mb-4 text-lg border-b-2 border-dw-rule pb-2 flex items-center gap-2">
                <span>🎯</span> Direcionais (Vol)
              </h4>
              <p className="mb-1"><strong>Strap</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-emerald-600 bg-emerald-50 border-emerald-200">alta</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-red-700 bg-red-50 border-red-200">Débito (Pagando)</span> — 2 calls + 1 put no mesmo strike. Long vol com viés de alta; ganho assimétrico p/ cima.</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> BBAS3 a R$28 (pré-balanço) — compra 2 calls R$28 e 1 put R$28, apostando em movimento forte com viés de alta.
              </div>
              <p className="mb-1"><strong>Strip</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-rose-600 bg-rose-50 border-rose-200">baixa</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-red-700 bg-red-50 border-red-200">Débito (Pagando)</span> — 2 puts + 1 call no mesmo strike. Long vol com viés de baixa; ganho assimétrico p/ baixo.</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> BOVA11 a R$130 (cenário de risco) — compra 2 puts R$130 e 1 call R$130, apostando em queda forte sem abrir mão de ganho na alta.
              </div>
            </div>
          </div>

          {/* Coluna 2 */}
          <div>
            <div className="mb-8">
              <h4 className="font-bold text-dw-blue mb-4 text-lg border-b-2 border-dw-rule pb-2 flex items-center gap-2">
                <span>🦎</span> Crédito Híbridas
              </h4>
              <p className="mb-1"><strong>Jade Lizard</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-amber-600 bg-amber-50 border-amber-200">renda</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-green-700 bg-green-50 border-green-200">Crédito (Recebendo)</span> — put OTM vendida + call spread de alta. Neutro/alta, short vol; sem risco de alta se o crédito ≥ largura do call spread.</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> MGLU3 a R$4,50 — vende put R$4,00 e um call spread R$5,00/R$5,50; se o crédito cobrir os R$0,50, não há risco na alta.
              </div>
              <p className="mb-1"><strong>Collar</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-purple-600 bg-purple-50 border-purple-200">hedge</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-slate-700 bg-slate-100 border-slate-300">Misto</span> — ação + put protetora + call coberta. Neutro/protegido; trava a posição numa banda (piso e teto).</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> ITUB4 a R$32 — tem a ação, compra put R$30 (piso) e vende call R$34 (teto), reduzindo o custo do seguro.
              </div>
              <p className="mb-1"><strong>Seagull</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-emerald-600 bg-emerald-50 border-emerald-200">alta</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-slate-700 bg-slate-100 border-slate-300">Misto</span> — call spread comprado + put vendida (bullish). Alta financiada pela put.</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> PETR4 a R$36 — compra o call spread R$36/R$40 financiado pela venda da put R$32; aposta de alta com custo baixo.
              </div>
              <p className="mb-1"><strong>Risk Reversal</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-emerald-600 bg-emerald-50 border-emerald-200">alta</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-slate-700 bg-slate-100 border-slate-300">Misto</span> — vende put OTM e compra call OTM. Direcional sintético via skew, quase sem custo.</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> VALE3 a R$58 — vende put R$54 e compra call R$62, montando uma comprada sintética quase sem custo.
              </div>
            </div>

            <div className="mb-8">
              <h4 className="font-bold text-dw-blue mb-4 text-lg border-b-2 border-dw-rule pb-2 flex items-center gap-2">
                <span>🔁</span> Sintéticas / Arbitragem
              </h4>
              <p className="mb-1"><strong>Box Spread</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-blue-600 bg-blue-50 border-blue-200">neutro</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-slate-700 bg-slate-100 border-slate-300">Travado</span> — bull call spread + bear put spread nos mesmos strikes. Renda fixa sintética; payoff travado = Δstrikes.</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> BOVA11 — bull call spread R$125/135 + bear put spread R$125/135; payoff travado em R$10, equivalente a uma taxa pré-fixada.
              </div>
              <p className="mb-1"><strong>Conversão</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-blue-600 bg-blue-50 border-blue-200">neutro</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-slate-700 bg-slate-100 border-slate-300">Travado</span> — ação + put − call no mesmo strike. Captura desvio de paridade put-call.</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> PETR4 a R$36 — compra a ação, compra put R$36 e vende call R$36, travando o resultado e capturando o desvio de paridade.
              </div>
              <p className="mb-1"><strong>Reversão</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-blue-600 bg-blue-50 border-blue-200">neutro</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-slate-700 bg-slate-100 border-slate-300">Travado</span> — inverso da conversão (vende ação + vende put + compra call).</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> VALE3 a R$58 — vende a ação, vende put R$58 e compra call R$58; captura o desvio de paridade no sentido oposto.
              </div>
              <p className="mb-1"><strong>Sintético Comprado</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-emerald-600 bg-emerald-50 border-emerald-200">alta</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-slate-700 bg-slate-100 border-slate-300">Misto</span> — compra call + vende put no mesmo strike. Replica a ação com menos capital.</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> ITUB4 a R$32 — compra call R$32 e vende put R$32, replicando a compra da ação com bem menos caixa.
              </div>
              <p className="mb-1"><strong>Sintético Vendido</strong> <span className="text-[10px] font-bold px-1.5 py-0.5 rounded border align-middle text-rose-600 bg-rose-50 border-rose-200">baixa</span> <span className="text-[10px] font-normal px-1.5 py-0.5 rounded border align-middle text-slate-700 bg-slate-100 border-slate-300">Misto</span> — vende call + compra put no mesmo strike. Replica a venda da ação; risco ilimitado na alta.</p>
              <div className="mb-3 mt-1 text-[13px] text-dw-ink-muted border-l-2 border-dw-blue/40 pl-3 italic">
                <strong>Exemplo:</strong> ABEV3 a R$12 — vende call R$12 e compra put R$12, replicando a venda da ação para lucrar na queda.
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
