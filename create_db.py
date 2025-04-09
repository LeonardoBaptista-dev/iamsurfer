from app import app, db

with app.app_context():
    print("Criando tabelas no banco de dados...")
    db.create_all()
    print("Tabelas criadas com sucesso!") 