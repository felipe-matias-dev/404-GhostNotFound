## O que muda

<!-- Uma ou duas frases. Link da issue: Closes #NN -->

## Como testar

<!-- Comandos ou passos para o revisor ver funcionando. -->

## Definition of Done

<!-- Marque o que se aplica; risque (~~item~~) o que não se aplica. Ver docs/planejamento.md §4.6. -->

- [ ] Roda via `docker compose up` ou pelo Job do Databricks
- [ ] CI verde (hooks, pytest, tipos e build do frontend, imagens Docker)
- [ ] Nomes de colunas, variáveis e rótulos seguem a linguagem ubíqua (`docs/arquitetura.md` §5)
- [ ] Documentado no README da pasta e/ou no dicionário de dados
- [ ] Decisão nova registrada em `docs/decisoes.md` (`DEC-NNN`)
- [ ] Mudou rota ou schema da API: `contracts/openapi.json` e `frontend/src/lib/api-schema.gen.ts` atualizados, revisão de outra frente
- [ ] IA: o golden set não regrediu
- [ ] Dados: contagens e chaves validadas; decisões de limpeza no log de qualidade
