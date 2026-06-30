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


def ensure_columns():
    """Adiciona colunas novas a tabelas já existentes (create_all não faz ALTER).

    ADD COLUMN é seguro e idempotente (só adiciona se faltar) e funciona tanto
    em SQLite quanto em PostgreSQL. Cobre os bancos que já existiam antes destas
    features (ex.: coordenadas das caronas).
    """
    from sqlalchemy import text

    specs = {
        'surf_trip': [
            ('departure_lat', 'FLOAT'), ('departure_lng', 'FLOAT'),
            ('destination_lat', 'FLOAT'), ('destination_lng', 'FLOAT'),
        ],
        'trip_participant': [
            ('meeting_lat', 'FLOAT'), ('meeting_lng', 'FLOAT'),
            ('meeting_label', 'VARCHAR(200)'),
        ],
        'notification': [
            ('related_spot_id', 'INTEGER'),  # alertas de swell ligam ao pico
        ],
        'post': [
            ('media_status', 'VARCHAR(20)'),  # fila assíncrona de processamento de mídia
        ],
        'spot': [
            ('best_season', 'VARCHAR(120)'),  # melhor época do ano
            ('water_temp', 'VARCHAR(40)'),    # temperatura média da água
        ],
    }
    # Colunas que precisaram ser alargadas (seleção múltipla / textos maiores).
    # ALTER COLUMN TYPE só é necessário no PostgreSQL; o SQLite ignora tamanho.
    widen = {
        'spot': [
            ('best_tide', 'VARCHAR(120)'),    # uma ou mais marés
            ('crowd_level', 'VARCHAR(60)'),   # "Cheio nos fins de semana"
        ],
    }
    with app.app_context():
        insp = db.inspect(db.engine)
        tables = insp.get_table_names()
        for table, cols in specs.items():
            if table not in tables:
                continue  # tabela nova: já veio completa do create_all
            have = {c['name'] for c in insp.get_columns(table)}
            for name, ddl in cols:
                if name not in have:
                    print(f"  + {table}.{name}")
                    db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))
        if db.engine.dialect.name == 'postgresql':
            for table, cols in widen.items():
                if table not in tables:
                    continue
                for name, ddl in cols:
                    print(f"  ~ {table}.{name} -> {ddl}")
                    db.session.execute(text(f'ALTER TABLE {table} ALTER COLUMN {name} TYPE {ddl}'))
        db.session.commit()


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
            # create_all é idempotente: cria apenas tabelas que ainda não existem
            # (ex.: Story/StoryView), sem alterar ou apagar as já existentes.
            db.create_all()
        init_db(create_schema=False)          # semeia (idempotente)
        print("Migrações aplicadas.")

    # Garante colunas novas em tabelas pré-existentes (ex.: coordenadas de carona)
    print("Verificando colunas novas...")
    ensure_columns()

    print("Inicialização concluída.")


if __name__ == '__main__':
    main()
