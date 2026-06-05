// Fonte única dos tickers da B3 usados no frontend (scanner + signals). [P1-2]
// Antes a lista era duplicada/divergente entre scanner/page.tsx e signals/page.tsx,
// o que obrigava a editar 2 arquivos ao tratar deslistados/renomeados. Aqui é a
// única definição; ambos derivam dela. (O backend mantém sua própria fonte em
// ATIVOS_B3 / ticker_loader; ver PLANO_DE_MELHORIAS para a unificação via API.)

export type Acao = { ticker: string; nome: string };

export const SECTORS: Record<string, Acao[]> = {
    'Todos': [],
    'Petróleo & Gás': [
        { ticker: 'PETR4', nome: 'Petrobras PN' },
        { ticker: 'PETR3', nome: 'Petrobras ON' },
        { ticker: 'PRIO3', nome: 'PRIO' },
        { ticker: 'BRAV3', nome: 'Brava Energia' },
        { ticker: 'RECV3', nome: 'PetroReconcavo' },
        { ticker: 'CSAN3', nome: 'Cosan' },
    ],
    'Mineração & Siderurgia': [
        { ticker: 'VALE3', nome: 'Vale' },
        { ticker: 'CSNA3', nome: 'CSN' },
        { ticker: 'GGBR4', nome: 'Gerdau PN' },
        { ticker: 'GGBR3', nome: 'Gerdau ON' },
        { ticker: 'USIM5', nome: 'Usiminas PNA' },
        { ticker: 'CMIN3', nome: 'CSN Mineração' },
        { ticker: 'GOAU4', nome: 'Metalúrgica Gerdau' },
    ],
    'Financeiro & Bancos': [
        { ticker: 'ITUB4', nome: 'Itaú Unibanco PN' },
        { ticker: 'ITUB3', nome: 'Itaú Unibanco ON' },
        { ticker: 'BBDC4', nome: 'Bradesco PN' },
        { ticker: 'BBDC3', nome: 'Bradesco ON' },
        { ticker: 'BBAS3', nome: 'Banco do Brasil' },
        { ticker: 'SANB11', nome: 'Santander' },
        { ticker: 'BPAC11', nome: 'BTG Pactual' },
        { ticker: 'B3SA3', nome: 'B3' },
        { ticker: 'IRBR3', nome: 'IRB Brasil' },
        { ticker: 'PSSA3', nome: 'Porto Seguro' },
        { ticker: 'BBSE3', nome: 'BB Seguridade' },
        { ticker: 'CXSE3', nome: 'Caixa Seguridade' },
    ],
    'Varejo': [
        { ticker: 'MGLU3', nome: 'Magazine Luiza' },
        { ticker: 'LREN3', nome: 'Lojas Renner' },
        { ticker: 'AZZA3', nome: 'Azzas 2154' },
        { ticker: 'ALPA4', nome: 'Alpargatas' },
        { ticker: 'LWSA3', nome: 'Locaweb' },
        { ticker: 'BHIA3', nome: 'Casas Bahia' },
    ],
    'Energia Elétrica': [
        { ticker: 'EGIE3', nome: 'Engie Brasil' },
        { ticker: 'TAEE11', nome: 'Taesa' },
        { ticker: 'ENGI11', nome: 'Energisa' },
        { ticker: 'CMIG4', nome: 'Cemig PN' },
        { ticker: 'CPFE3', nome: 'CPFL Energia' },
        { ticker: 'SBSP3', nome: 'Sabesp' },
        { ticker: 'ELET3', nome: 'Eletrobras ON' },
        { ticker: 'ELET6', nome: 'Eletrobras PNB' },
        { ticker: 'TRPL4', nome: 'ISA CTEEP' },
        { ticker: 'AURE3', nome: 'Auren Energia' },
        { ticker: 'ENEV3', nome: 'Eneva' },
        { ticker: 'CPLE6', nome: 'Copel PNB' },
    ],
    'Industrial & Bens de Capital': [
        { ticker: 'WEGE3', nome: 'WEG' },
        { ticker: 'EMBR3', nome: 'Embraer' },
        { ticker: 'RAIL3', nome: 'Rumo' },
        { ticker: 'MOVI3', nome: 'Movida' },
        { ticker: 'RENT3', nome: 'Localiza' },
        { ticker: 'RAPT4', nome: 'Randon PN' },
        { ticker: 'POMO4', nome: 'Marcopolo PN' },
    ],
    'Consumo & Alimentos': [
        { ticker: 'ABEV3', nome: 'Ambev' },
        { ticker: 'BRFS3', nome: 'BRF' },
        { ticker: 'JBSS3', nome: 'JBS' },
        { ticker: 'MRFG3', nome: 'Marfrig' },
        { ticker: 'SMTO3', nome: 'São Martinho' },
        { ticker: 'BEEF3', nome: 'Minerva' },
        { ticker: 'SLCE3', nome: 'SLC Agrícola' },
    ],
    'Telecom': [
        { ticker: 'VIVT3', nome: 'Vivo' },
        { ticker: 'TIMS3', nome: 'TIM' },
    ],
    'Saúde': [
        { ticker: 'RDOR3', nome: "Rede D'Or" },
        { ticker: 'HAPV3', nome: 'Hapvida' },
        { ticker: 'DASA3', nome: 'Dasa' },
        { ticker: 'FLRY3', nome: 'Fleury' },
        { ticker: 'QUAL3', nome: 'Qualicorp' },
    ],
    'Imobiliário & Construção': [
        { ticker: 'MRVE3', nome: 'MRV' },
        { ticker: 'CYRE3', nome: 'Cyrela' },
        { ticker: 'EVEN3', nome: 'Even' },
        { ticker: 'EZTC3', nome: 'EZTec' },
        { ticker: 'TEND3', nome: 'Tenda' },
    ],
    'Educação': [
        { ticker: 'COGN3', nome: 'Cogna' },
        { ticker: 'YDUQ3', nome: 'YDUQS' },
    ],
    'Papel & Celulose': [
        { ticker: 'SUZB3', nome: 'Suzano' },
        { ticker: 'KLBN11', nome: 'Klabin' },
        { ticker: 'DXCO3', nome: 'Dexco' },
    ],
    'Transporte & Logística': [
        { ticker: 'AZUL4', nome: 'Azul' },
        { ticker: 'GOLL4', nome: 'Gol' },
        { ticker: 'ECOR3', nome: 'EcoRodovias' },
    ],
    'Tech & Serviços': [
        { ticker: 'TOTVS3', nome: 'Totvs' },
    ],
};

// Lista plana de códigos (sem o pseudo-setor 'Todos'), usada pelo scan completo.
export const ALL_B3_TICKERS: string[] = Object.entries(SECTORS)
    .filter(([setor]) => setor !== 'Todos')
    .flatMap(([, acoes]) => acoes.map((a) => a.ticker));
