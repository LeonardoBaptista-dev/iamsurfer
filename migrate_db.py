"""Prepara o banco para a aplicação (schema + dados iniciais).

Não usa o CLI `flask db` (quebrado neste ambiente) — usa a API Python do
Flask-Migrate.

O histórico de migrações deste projeto não cria as tabelas a partir do zero
(sempre dependeu de create_all), então:

- Banco NOVO  -> cria o schema completo a partir dos models (create_all) e
                 marca a revisão atual como aplicada (stamp head). Assim,
                 migrações FUTURAS rodam normalmente via upgrade().
- Banco EXISTENTE -> aplica as migrações pendentes (upgrade), o que cobre as
                 mudanças novas (ex.: points, selos) em bancos que já têm dados.
"""
import sys

from app import app, db, init_db, wait_for_db
from flask_migrate import upgrade, stamp


def main():
    if not wait_for_db():
        print("Banco de dados indisponível. Abortando.", file=sys.stderr)
        sys.exit(1)

    with app.app_context():
        existing_tables = db.inspect(db.engine).get_table_names()

    if 'user' not in existing_tables:
        print("Banco novo: criando schema a partir dos models e marcando head...")
        init_db(create_schema=True)          # importa models + create_all + semeia
        with app.app_context():
            stamp()                           # alembic_version = head
        print("Schema criado e marcado como atual (head).")
    else:
        print("Banco existente: aplicando migrações pendentes...")
        with app.app_context():
            upgrade()                         # aplica migrações novas (points, selos, ...)
        init_db(create_schema=False)          # semeia (idempotente)
        print("Migrações aplicadas.")

    print("Inicialização concluída.")


if __name__ == '__main__':
    main()
