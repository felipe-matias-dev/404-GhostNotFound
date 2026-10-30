#!/bin/bash
# Roda uma única vez, na primeira subida do container (volume de dados vazio).
# Para reaplicar depois de editar: docker compose down -v && docker compose up -d
set -euo pipefail

# Usuários valem para o servidor inteiro, então são criados uma vez só.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-SQL
	CREATE DATABASE venergy_test OWNER "$POSTGRES_USER";
	CREATE ROLE venergy_agent LOGIN PASSWORD '$AGENT_DB_PASSWORD';
	-- Segunda trava: mesmo com permissão, toda transação do agente nasce somente leitura.
	ALTER ROLE venergy_agent SET default_transaction_read_only = on;
	-- Teto no banco, acima do timeout de cada consulta do agente.
	ALTER ROLE venergy_agent SET statement_timeout = '30s';
SQL

# O banco da aplicação e o de testes têm a mesma estrutura.
for database in "$POSTGRES_DB" venergy_test; do
	psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$database" <<-SQL
		-- gold: tabelas recarregáveis a partir dos CSVs. app: dados criados no portal
		-- (ordens de inspeção), que a recarga da Gold nunca toca. semantic: as views do agente.
		CREATE SCHEMA gold;
		CREATE SCHEMA app;
		CREATE SCHEMA semantic;

		-- O agente só enxerga as views de semantic, e só para leitura. Elas leem a Gold com a
		-- permissão do dono, então ele não precisa de acesso a gold nem a app.
		GRANT CONNECT ON DATABASE "$database" TO venergy_agent;
		GRANT USAGE ON SCHEMA semantic TO venergy_agent;
		ALTER DEFAULT PRIVILEGES IN SCHEMA semantic GRANT SELECT ON TABLES TO venergy_agent;
	SQL
done
