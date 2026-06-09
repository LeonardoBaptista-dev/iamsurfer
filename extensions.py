from flask_sqlalchemy import SQLAlchemy

# Instância global do banco - importada por app.py e pelos models/routes
# Evita o circular import: models/routes importam daqui, não de app.py
db = SQLAlchemy()
