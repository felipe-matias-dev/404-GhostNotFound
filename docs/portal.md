# Guia do portal

Cada tela responde à pergunta de uma pessoa da V-Energy. O login define o cargo: a sidebar
destaca as telas dele em **Minha área** e mantém as demais em **Outras consultas**, sem
duplicações ([DEC-049](decisoes.md#dec-049--login-com-cookie-httponly-e-perfis-por-cargo)).
Logins de demonstração: [instalação](instalacao.md#logins-de-demonstração).

| Quem | Pergunta | Onde é respondida | Estado |
|---|---|---|---|
| **Henrique**, diretor comercial | Por que a receita não acompanhou a tarifa, e onde ela caiu? | [Visão geral e Receita](#visão-geral-e-receita-henrique) | Pronto |
| **Rafael**, gerente de perdas | Quais unidades inspecionar primeiro, e em que pé está cada ordem? | [Perdas](#perdas-rafael) | Pronto |
| **Camila**, atendimento | O que aconteceu com esta unidade consumidora, e por que a conta veio alta? | [Consulta de UC](#consulta-de-uc-camila) | Pronto |
| **Beatriz**, operação | Quais alimentadores e regiões têm o pior DEC e FEC, quem piorou e por que a luz cai? | [Rede](#rede-beatriz) | Pronto |
| **Patrícia**, diretora de TI | Os dados são confiáveis e seguros? Dá para perguntar em português? | [Agente de IA e auditoria](#agente-de-ia-e-auditoria-patrícia) | Pronto: tela do agente, chat flutuante e auditoria |

## Filtros compartilhados

As telas de análise compartilham o recorte: a barra superior grava na URL município, bairro,
classe e o par de períodos, de modo que Visão geral, Receita, Rede e Perdas descrevem o mesmo
recorte e um link reproduz a análise; os filtros próprios de cada tela ficam só na sessão do
navegador ([DEC-060](decisoes.md#dec-060--filtros-compartilhados-entre-as-telas-do-portal)).

- Em Perdas o período é apenas contexto, porque a fila é um retrato da Gold e as ordens de
  inspeção são estado atual; e a consulta individual de UC mostra o histórico completo, sem o
  recorte da análise ([DEC-058](decisoes.md#dec-058--período-é-contexto-em-perdas-e-a-consulta-de-uc-não-é-limitada-pelo-recorte)).
- A ordem de uma UC que saiu do cadastro da Gold continua na lista sem recorte e fica fora
  quando há recorte, já que a localização só existe no cadastro
  ([DEC-059](decisoes.md#dec-059--ordem-de-uc-ausente-do-cadastro-da-gold-fica-fora-da-lista-quando-há-recorte)).

## Visão geral e Receita (Henrique)

- **Visão geral:** indicadores comercial, de rede e de atendimento do recorte.
- **Receita:** ponte em cascata, mapa da Região Metropolitana do Recife e drill-down
  município → bairro → classe.
- **Insight de IA:** fica ao lado da frase de leitura da ponte e só chama o modelo quando a
  pessoa clica em **Gerar insight**. O texto narra um JSON de métricas da Gold e é descartado
  se citar um número que não está nele
  ([DEC-069](decisoes.md#dec-069--insight-de-ia-ao-lado-da-leitura-que-ele-narra)).

O método por trás da ponte: [diagnóstico da receita](diagnostico-receita.md).

## Rede (Beatriz)

- DEC, FEC, horas interrompidas, interrupções e UCs do recorte contra o período base.
- Ranking de alimentadores no recorte, ranking de todos os bairros ou descida
  município → bairro → alimentador, com a variação de cada linha contra a base, busca,
  ordenação por coluna e trilha no topo.
- No alimentador, DEC e FEC mensais dentro do recorte contra o recorte inteiro e
  **Por que cai**: horas por causa e por tipo, UCs atingidas e reincidentes, duração das
  ocorrências e as UCs mais atingidas.

A Rede também localiza a continuidade num mapa único da RMR: o mesmo seletor **DEC | FEC** da
tabela troca a cor dos municípios e dos bairros. DEC mede horas sem energia por UC; FEC,
interrupções por UC. A intensidade vai de zero ao maior índice das regiões da malha no período
e classe escolhidos, sem classificar conformidade regulatória. Clicar filtra a tela; regiões sem
correspondência geográfica continuam na tabela, com aviso no mapa.

O DEC e o FEC de um recorte saem da soma dos componentes dividida pela média mensal de UCs, no
backend, e não da média dos alimentadores
([DEC-033](decisoes.md#dec-033--dec-e-fec-por-período-e-recorte-e-a-fila-de-suspeitas-paginada),
[DEC-071](decisoes.md#dec-071--tela-de-rede-indicadores-do-recorte-contra-a-base-e-histórico-contra-a-empresa),
[DEC-072](decisoes.md#dec-072--tela-de-rede-quem-piorou-onde-atacar-e-por-que-cai)).

## Perdas (Rafael)

Fila de suspeitas com filtros, seleção em lote e geração de ordens; ordens de inspeção em
Kanban ou tabela, com enviar a campo, concluir, cancelar, tempo por etapa e planilha de campo.

- **Indicadores e mapa:** no topo, suspeitas, suspeitas sem ordem ativa, ordens geradas e em
  campo, e a taxa de irregularidade das vistorias do portal ao lado da histórica da Gold
  (`gold_inspecoes_uc`). O mapa e o ranking mostram as suspeitas e o kWh/mês estimado por
  município ou pelos bairros do município; clicar aplica o recorte compartilhado. Tudo vem
  pronto de `GET /fila-suspeitas/indicadores` e `GET /fila-suspeitas/recortes`
  ([DEC-076](decisoes.md#dec-076--tela-de-perdas-indicadores-mapa-última-inspeção-e-filtros-novos-da-fila)).
- **Ciclo da ordem:** `GERADA → EM_CAMPO → CONCLUIDA` ou `CANCELADA`, com volta de `EM_CAMPO`
  para `GERADA`, e no máximo uma ordem ativa por UC, garantida no banco
  ([DEC-009](decisoes.md#dec-009--modelo-das-ordens-de-inspeção),
  [DEC-048](decisoes.md#dec-048--ordem-em-campo-pode-voltar-para-gerada)). Só o perfil
  `perdas` altera ordens.
- **Contexto e resultado:** cada ordem guarda a posição, os motivos e o kWh/mês estimado da UC
  na fila no momento da geração. Concluir como irregularidade confirmada exige o tipo e o kWh
  recuperado, pela tela ou pela planilha
  ([DEC-075](decisoes.md#dec-075--ordem-de-inspeção-guarda-o-contexto-da-fila-e-o-resultado-de-campo)).
- **Filtros da fila:** combinam queda de consumo, medidor eletromecânico, leituras estimadas,
  **Somente UCs sem ordem ativa** e **Ocultar UCs inspecionadas nos últimos** 6, 12, 24 ou 36
  meses (vistoria da Gold ou do portal). A Gold só informa leituras estimadas a partir de 25%;
  o filtro aceita de 25% a 100% e não inclui percentuais inferiores ou desconhecidos. Os
  filtros atuam antes da paginação
  ([DEC-051](decisoes.md#dec-051--filtro-de-queda-na-fila-de-suspeitas)). A coluna
  **Última inspeção** mostra data, resultado e origem, e a barra soma o kWh/mês estimado das
  UCs selecionadas.
- **Planilha de campo:** o botão de baixar exporta as ordens em campo no formato de
  `inspecoes.xlsx`, com seleção em resultado, data e kWh. O de enviar liga cada linha
  à ordem em campo da UC, conclui as válidas e mostra a tabela das rejeitadas com o motivo.
  Reenviar o mesmo arquivo não muda nada
  ([DEC-062](decisoes.md#dec-062--planilha-de-campo-exportar-as-ordens-em-campo-e-subir-o-resultado)).
- **Atualização ao vivo:** quem muda uma ordem avisa as telas abertas pelo Postgres
  (`pg_notify` → SSE), e elas refazem a consulta sem recarregar a página
  ([DEC-063](decisoes.md#dec-063--ordens-de-inspeção-em-tempo-real-aviso-no-commit-e-sse)).
- **Tempo parado:** cada cartão mostra há quanto tempo a ordem está no status atual e o selo
  **Atrasada** (mais de 5 dias gerada ou 10 em campo, ajustáveis no `.env`).
  `GET /ordens-inspecao/tempos-por-etapa` dá a mediana e o p90 por etapa
  ([DEC-064](decisoes.md#dec-064--tempo-das-ordens-no-status-e-por-etapa)).

## Consulta de UC (Camila)

Use **Consulta de UC** na sidebar ou Ctrl/Cmd + K para abrir a palette. Busque pelo código
exatamente como aparece na conta, preservando zeros iniciais, ou selecione uma consulta recente.
Somente os cinco códigos consultados com sucesso mais recentemente ficam salvos neste navegador,
sem titular ou valores; a ação **Limpar recentes** remove a lista.

O link `/uc?cod_uc=0001` continua abrindo a visão 360 diretamente. Sem código, `/uc` tem uma
entrada compacta para abrir a busca. A palette valida a consulta antes de navegar e a tela
reúne cadastro mascarado, consumo, contas pendentes, medidor/GD, interrupções e chamados em
uma única consulta: `GET /unidades-consumidoras/{cod_uc}/visao-360`. A rota antiga de cadastro
permanece disponível. O fluxo de entrada e os limites do histórico local estão na DEC-043.

O diagnóstico segue a DEC-044 e o `Uc360Schema` aprovado no PR #55: a referência é a última
competência **de toda a Gold**, não a última fatura da UC. A tendência vem do backend:
alta acima de +10%, queda abaixo de −10% e estabilidade na faixa inclusiva de ±10%.
Estabilidade pode incluir uma alta de 5%; a tela mostra os percentuais fornecidos pela API.
A variação de 12 meses considera somente pares com fatura e informa `meses_comparados`.
Lacunas são desconhecidas, não zero; base zero não tem percentual. Faturas pendentes não têm
corte por período e os históricos são paginados somente na apresentação. A Gold é histórica,
não indica falta de energia em tempo real. Diferenças da apresentação e limites em
[DEC-042](decisoes.md#dec-042--visão-360-da-uc-e-comparação-sazonal-do-consumo).
A diferença absoluta em kWh não aparece na tela porque não está no contrato aprovado; não é
simulada por outras chamadas.

### Por que a conta mudou

O card no topo da tela responde à reclamação de conta alta em reais: a conta do mês de
referência contra a do mesmo mês do ano anterior, com a diferença dividida em consumo, tarifa,
bandeira e tributos, e a parte que mais pesou na direção da conta destacada. Os dias que cada
conta cobriu aparecem só como texto, sem entrar na divisão. As partes vêm prontas de
`variacao_conta`, na mesma rota da visão 360, e somam exatamente a diferença; a tela não faz
conta. Sem a conta do ano anterior, o card diz que não há com o que comparar, e uma leitura
estimada ganha um aviso. Fórmula e limites em
[DEC-057](decisoes.md#dec-057--variação-da-conta-da-unidade-consumidora-dividida-por-motivo).

## Agente de IA e auditoria (Patrícia)

Perguntas em português em `POST /ai/ask`, com cada resposta auditada e legível em
`GET /ai/audit/{id}` pelo perfil `ti`. Como o agente decide responder, esclarecer ou dizer que
não sabe: [agente de IA](agente-ia.md).

## Login

`/login` integrado ao cookie, menu e entrada por cargo, retorno a links de dados após
autenticar e saída com limpeza do cache. A entrada usa a marca animada e uma rede elétrica
ilustrativa, com pausa e movimento reduzido; detalhes em
[Login e perfis](../frontend/README.md#login-e-perfis).
