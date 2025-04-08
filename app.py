from flask import Flask, Markup
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os
from dotenv import load_dotenv
import time

# Carrega variáveis de ambiente
load_dotenv()

# Inicializa a aplicação Flask
app = Flask(__name__, instance_relative_config=True)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uma_chave_secreta_temporaria')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///iamsurfer.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')

# Certifica-se de que a pasta instance existe
os.makedirs(app.instance_path, exist_ok=True)

# Filtro personalizado para transformar quebras de linha em <br>
@app.template_filter('nl2br')
def nl2br(value):
    if value:
        return Markup(value.replace('\n', '<br>'))
    return value

# Inicializa o SQLAlchemy
db = SQLAlchemy(app)

# Inicializa o sistema de login
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'

# Inicializa o Flask-Migrate
migrate = Migrate(app, db)

# Certifica-se de que o diretório de uploads existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'posts'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'profile_pics'), exist_ok=True)

# Importa os modelos e rotas depois de inicializar o db
from models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Função para esperar o banco de dados inicializar
def wait_for_db():
    if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
        max_retries = 5
        for attempt in range(max_retries):
            try:
                with app.app_context():
                    print(f"Tentando conectar ao banco de dados (tentativa {attempt+1}/{max_retries})...")
                    db.engine.connect()
                    print("Conexão com o banco de dados estabelecida!")
                    return True
            except Exception as e:
                print(f"Falha ao conectar ao banco de dados: {e}")
                if attempt < max_retries - 1:
                    print("Tentando novamente em 5 segundos...")
                    time.sleep(5)
                else:
                    print("Número máximo de tentativas atingido. Falha ao conectar ao banco de dados.")
                    return False
    return True

# Inicializa o banco de dados e cria usuário admin
def init_db():
    with app.app_context():
        db.create_all()
        
        # Cria um usuário admin se não existir nenhum usuário
        if User.query.count() == 0:
            admin = User(
                username="admin",
                email="admin@iamsurfer.com",
                is_admin=True,
                profile_image="uploads/default_profile.jpg"
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("Usuário admin criado com sucesso!")

# Importa e registra os blueprints
try:
    from routes.auth import auth
    from routes.main import main
    from routes.posts import posts
    from routes.admin import admin
    from routes.messages import messages

    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(posts)
    app.register_blueprint(admin)
    app.register_blueprint(messages)
except ImportError as e:
    print(f"Erro ao importar blueprints: {e}")

if __name__ == '__main__':
    if wait_for_db():
        init_db()
        app.run(debug=True, host='0.0.0.0')
else:
    # Para quando estiver rodando com Flask CLI (gunicorn, etc)
    wait_for_db()
    init_db() 