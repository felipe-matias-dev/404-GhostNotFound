# Documentação do V-Energy Grid 360

Comece pelo [README da raiz](../README.md) para a visão geral e a instalação rápida. Daqui
em diante, cada documento aprofunda um assunto.

## Comece aqui

| Documento | O que tem |
|---|---|
| [Instalação e operação local](instalacao.md) | Docker Compose passo a passo, logins, chave do Gemini, `make`, observabilidade e problemas comuns |
| [Dos arquivos brutos ao portal](dados-brutos.md) | Upload no Databricks, Workflow, download da Gold, carga no banco e agendamento |
| [Guia do portal](portal.md) | Cada tela por perfil: Receita, Rede, Perdas, Consulta de UC e filtros compartilhados |
| [Agente de IA](agente-ia.md) | Status das respostas, camadas de segurança e resultados da avaliação |

## Entenda o projeto

| Documento | O que tem |
|---|---|
| [Diagnóstico da receita](diagnostico-receita.md) | A resposta ao Henrique: hipóteses H1 a H8, ponte PVM e recomendações |
| [Confiabilidade e decisões em destaque](confiabilidade.md) | Por que confiar nos números e as decisões que mais mudam o produto |
| [Arquitetura e domínio](arquitetura.md) | Visão geral do sistema, pilha, subdomínios, linguagem ubíqua, modelo da Gold e ADRs |

## Referência

| Documento | O que tem |
|---|---|
| [Decisões e suposições](decisoes.md) | Cada decisão `DEC-NNN` com motivo, alternativa descartada e autor |
| [Dicionário de dados](dicionario-de-dados.md) | Definição de cada coluna e métrica da Gold |
| [Qualidade dos dados](qualidade-dados.md) | Os 47 problemas do dataset e a regra aplicada a cada um |
| [Contrato da Gold](../contracts/gold_schema.yaml) | Tabelas, colunas, tipos e consumidores da Gold |
| [Spec do agente](../ai-agent/docs/specs/2026-10-19-architecture-design.md) | Contrato, segurança e avaliação do agente de IA |

## Processo

| Documento | O que tem |
|---|---|
| [Contribuindo](contribuindo.md) | Estrutura do repositório, regras do time, hooks e CI |
| [Planejamento](planejamento.md) e [backlog](backlog.md) | Cronograma, hipóteses iniciais, épicos e histórias |

## Por módulo

| Módulo | README |
|---|---|
| Engenharia de dados | [`data-engineering/README.md`](../data-engineering/README.md) |
| Backend | [`backend/README.md`](../backend/README.md) |
| Frontend | [`frontend/README.md`](../frontend/README.md) |
| Agente de IA | [`ai-agent/README.md`](../ai-agent/README.md) |
