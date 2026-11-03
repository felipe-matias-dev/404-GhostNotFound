# Confiabilidade e decisões em destaque

Por que confiar nos números que o portal e o agente mostram, e as decisões que mais mudam o
produto. O registro completo, com todas as decisões numeradas e as suposições, está em
[decisões](decisoes.md).

## Por que confiar nos números

- **O pipeline para antes de publicar dado errado.** Os notebooks conferem cada camada com travas como `exigir_sem_perda`, `exigir_chave_unica`, `exigir_sem_orfaos` e `exigir_mesma_contagem`. Na Gold, por exemplo: Gold + linhas excluídas = Silver, `efeito_preco = efeito_tarifa + efeito_bandeira` e nenhuma competência faltando. Uma falha interrompe o Job antes de exportar os CSVs ([DEC-039](decisoes.md#dec-039--workflow-do-databricks-e-agendamento-mensal)).
- **Os problemas do dataset estão catalogados, não escondidos.** São 47 problemas em 8 fontes, mais 5 conferências cruzadas, cada um com a regra aplicada ([qualidade dos dados](qualidade-dados.md)). Exemplo: as 8.016 leituras negativas são 6.299 trocas de medidor e 1.717 sinais invertidos, e as duas regras reproduzem o valor que a fatura cobrou.
- **O contrato da Gold é conferido no CI.** `backend/tests/test_contrato_gold.py` compara o YAML com os modelos e com a carga (nome, tipo, nulidade, chave). Se Dados mudar uma coluna, o CI aponta antes de a Gold real falhar na carga ([DEC-014](decisoes.md#dec-014--o-backend-espelha-o-contrato-da-gold)).
- **A carga aguenta a Gold real.** São ~4 milhões de linhas em lotes de 10 mil, com pico de ~110 MB de memória. A primeira versão crescia ~1,9 KB por linha e derrubou um notebook de 8 GB. Uma rodada confere todos os arquivos antes de apagar a Gold anterior ([DEC-038](decisoes.md#dec-038--carga-da-gold-em-lotes-com-uma-rodada-de-conferência-antes-de-gravar)).
- **Testes em todas as frentes.**

  | Frente | Testes | Onde rodam |
  |---|---|---|
  | Backend | 211 funções `pytest` | CI, contra um Postgres de verdade |
  | Agente de IA | 248 funções `pytest`, inclusive integração com o banco | CI, contra um Postgres de verdade |
  | Frontend | 46 casos Vitest e 24 stories no Storybook | CI, com checagem de tipos e build |

## Decisões que defendemos

**PostgreSQL com schemas `gold` e `app`** · [DEC-002](decisoes.md#dec-002--banco-local-postgresql)
- **Problema:** o agente precisa de um usuário que só lê, e a recarga da Gold não pode apagar o trabalho de campo.
- **Decisão:** Postgres 17 em Docker, com o usuário `venergy_agent` limitado ao `SELECT` no schema `gold`.
- **Descartado:** SQLite, que dispensa instalação mas não tem usuários nem schemas.
- **Efeito:** o somente leitura do agente é garantido pelo banco, e as ordens de inspeção do Rafael sobrevivem a cada recarga.

**Login com cookie httpOnly e perfil checado no backend** · [DEC-049](decisoes.md#dec-049--login-com-cookie-httponly-e-perfis-por-cargo)
- **Problema:** esconder um item do menu não impede quem chama a API direto, e a auditoria do agente guarda a pergunta de todo mundo.
- **Decisão:** `POST /auth/login` grava um JWT de 8 horas num cookie `HttpOnly` com `SameSite=Lax`; cinco perfis, com a escrita nas ordens só para `perdas` e a auditoria só para `ti`. O menu por cargo dá foco, e a permissão mora no backend.
- **Descartado:** token no `localStorage`, que um XSS lê; e bloquear a leitura por tela, porque o agente já lê toda a Gold.
- **Efeito:** sem login a API responde 401 e com o perfil errado, 403; o Rafael é o único que mexe nas ordens de inspeção.
- **Portal:** `/login` integrado ao cookie, menu e entrada por cargo, retorno a links de dados após autenticar e saída com limpeza do cache. A entrada usa a marca animada e uma rede elétrica ilustrativa, com pausa e movimento reduzido; detalhes em [Login e perfis](../frontend/README.md#login-e-perfis).

**Limite de tentativas de login, sem captcha** · [DEC-065](decisoes.md#dec-065--limite-de-tentativas-de-login-por-login-e-endereço)
- **Problema:** o login não tinha freio, e o portal tem cinco logins conhecidos para alguém testar senhas.
- **Decisão:** cinco senhas erradas do mesmo login e do mesmo endereço em 15 minutos bloqueiam o par (`429` com o tempo de espera). Bloqueado, nem a senha certa entra, e a resposta é igual para login que existe ou não. O contador fica no banco, e as tentativas simultâneas passam uma de cada vez.
- **Descartado:** captcha, que depende de serviço externo e de internet e quebraria o teste do clone limpo; e bloquear só pelo login, que deixaria qualquer um trancar a conta do Rafael.
- **Efeito:** o chute de senha para depois de cinco tentativas, sem dependência nova. Atrás de um proxy (Vite, Docker) o endereço é o do proxy, e o limite vira por login; está na decisão.

**Ordens de inspeção como máquina de estados garantida no banco** · [DEC-009](decisoes.md#dec-009--modelo-das-ordens-de-inspeção)
- **Decisão:** status `GERADA → EM_CAMPO → CONCLUIDA` ou `CANCELADA` (com volta de `EM_CAMPO` para `GERADA`, [DEC-048](decisoes.md#dec-048--ordem-em-campo-pode-voltar-para-gerada)), histórico em `app.ordem_evento` e no máximo uma ordem ativa por unidade consumidora, garantida por índice único parcial.
- **Por que no banco:** uma checagem só no Python deixaria passar duas requisições simultâneas.
- **Sem FK para a Gold:** a carga apagaria as ordens ou falharia.
- **Descartado:** rotas por ação (`/concluir`, `/cancelar`), que espalham a validação.
- **Efeito:** cada visita fica no histórico, e o resultado registrado mede se a fila de suspeitas acerta.

**Planilha de campo: exportar as ordens em campo e subir o resultado** · [DEC-062](decisoes.md#dec-062--planilha-de-campo-exportar-as-ordens-em-campo-e-subir-o-resultado)
- **Problema:** a equipe volta de campo com uma planilha, e digitar cada resultado ordem por ordem é o retrabalho que o Rafael quer evitar.
- **Decisão:** `GET /ordens-inspecao/planilha` exporta as ordens em campo no formato de `inspecoes.xlsx`, e `POST /ordens-inspecao/planilha` liga cada linha à ordem em campo da unidade consumidora, conclui as válidas e devolve as rejeitadas com o motivo. As regras de limpeza são as da Silver (grafias do resultado, datas, vírgula decimal), mais o ponto de milhar digitado à mão.
- **Descartado:** tudo ou nada, porque uma linha escrita errada travaria o arquivo inteiro; e concluir ordem que ainda não foi enviada a campo, que pularia a máquina de estados.
- **Efeito:** a planilha exportada volta pelo upload sem remontar nada, reenviar o mesmo arquivo não muda nada, e o histórico mostra quem subiu a planilha. Tipo, kWh, data e inspetor ficam no texto da observação. A tela de Perdas tem os botões de baixar e de enviar, com a tabela das linhas rejeitadas; a planilha sai com seleção em resultado, data e kWh.

**Tela de ordens que se atualiza sozinha** · [DEC-063](decisoes.md#dec-063--ordens-de-inspeção-em-tempo-real-aviso-no-commit-e-sse)
- **Problema:** dois analistas de perdas olham a mesma ordem, e quem não recarrega a página vê o status antigo.
- **Decisão:** quem muda uma ordem dispara um `pg_notify` do Postgres na mesma transação, e `GET /ordens-inspecao/eventos` (SSE) repassa o aviso às telas abertas, que refazem a consulta. Um lote ou uma planilha é um aviso só.
- **Descartado:** WebSocket, porque o fluxo é só do servidor para a tela, e uma fila em memória, que avisaria antes do commit.
- **Efeito:** o aviso só sai se o banco confirmou a mudança. Com 20 mudanças simultâneas da mesma ordem, uma passa, 19 recebem 409 e as telas são avisadas uma vez (`python -m venergy_api.demo_concorrencia`).

**Quanto tempo cada ordem está parada** · [DEC-064](decisoes.md#dec-064--tempo-das-ordens-no-status-e-por-etapa)
- **Problema:** uma ordem esquecida em campo só aparecia para quem abria o histórico dela.
- **Decisão:** cada cartão do Kanban mostra há quanto tempo a ordem está no status atual, contando ao vivo, e o selo "Atrasada" (mais de 5 dias gerada ou 10 em campo, prazos supostos e ajustáveis no `.env`). `GET /ordens-inspecao/tempos-por-etapa` dá a mediana e o p90 por etapa, com o número de passagens.
- **Descartado:** calcular o tempo no navegador a partir da data, porque o relógio errado do computador daria um contador errado; e a média, que uma ordem esquecida distorce.
- **Efeito:** o Rafael vê o que está parado sem abrir ordem por ordem. O tempo sai do histórico das ordens, que é dado do backend, e não da Gold.

**DEC e FEC calculados a partir dos componentes** · [DEC-033](decisoes.md#dec-033--dec-e-fec-por-período-e-recorte-e-a-fila-de-suspeitas-paginada)
- **Problema:** DEC e FEC não se somam nem se tiram a média entre alimentadores ou bairros.
- **Decisão:** o indicador de um recorte sai da soma dos componentes dividida pela média mensal de unidades consumidoras, no backend.
- **Efeito:** a Beatriz vê o DEC de um bairro calculado do jeito certo, e não a média dos alimentadores.

**Decomposição gravada só para os mesmos meses em anos diferentes** · [DEC-028](decisoes.md#dec-028--pares-de-períodos-da-decomposição-e-o-que-fica-para-o-backend)
- **Problema:** o efeito preço e o efeito mix não se somam mês a mês, então cada par de períodos precisa ser calculado inteiro.
- **Decisão:** gravar só os pares de mesmos meses em anos diferentes, cerca de 1 milhão de linhas.
- **Descartado:** gravar todas as combinações de intervalos, que passariam de 1 bilhão de linhas e misturariam a sazonalidade.

**Carga em lotes com conferência antes de gravar** · [DEC-038](decisoes.md#dec-038--carga-da-gold-em-lotes-com-uma-rodada-de-conferência-antes-de-gravar)
- **Medição:** com 4 milhões de linhas, a memória caiu de ~7,8 GB (extrapolados) para 109 MB, em ~7 minutos.
- **Descartado:** `COPY` do Postgres, que exigiria converter listas, decimais e datas para o formato dele, e a validação linha a linha continuaria necessária.

**Agente só sobre views validadas por parser, e o LLM só narra** · [ADR-03 e ADR-04](arquitetura.md#7-decisões-técnicas)
- **Descartado:** SQL livre e ferramentas parametrizadas.
- **Efeito:** mesmo com o prompt manipulado, o banco não aceita escrita. O insight das telas narra um JSON de métricas da Gold e é descartado se citar um número que não está nele. No portal, ele fica ao lado da leitura do gráfico que narra e só chama o modelo quando a pessoa clica em **Gerar insight** ([DEC-069](decisoes.md#dec-069--insight-de-ia-ao-lado-da-leitura-que-ele-narra)).

**Workflow mensal e reprocessamento completo** · [DEC-039](decisoes.md#dec-039--workflow-do-databricks-e-agendamento-mensal)
- **Agendamento:** dia 6, D+5 do fechamento do faturamento. Os detalhes estão em [dos arquivos brutos ao portal](dados-brutos.md#agendamento-do-workflow).
