from flask import Flask, Markup, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os
from dotenv import load_dotenv
import time
import re
from cloud_storage import init_cloudinary

# Carrega variáveis de ambiente
load_dotenv()

# Inicializa a aplicação Flask
app = Flask(__name__, instance_relative_config=True)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uma_chave_secreta_temporaria')

# Configuração do banco de dados
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    # O Render usa 'postgresql://' em vez de 'postgres://'
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///iamsurfer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')

# Aumenta o limite máximo de upload para 16MB
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Verificar se está em ambiente de produção (Render)
is_production = os.environ.get('RENDER', False) or os.environ.get('FLASK_ENV') == 'production'

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

# Rota de health check para monitoramento do Render
@app.route('/healthz')
def health_check():
    try:
        # Verifica se consegue conectar ao banco de dados
        with app.app_context():
            db.engine.execute('SELECT 1')
        return jsonify(status='healthy', db_connection='ok'), 200
    except Exception as e:
        return jsonify(status='unhealthy', error=str(e)), 500

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
    """Inicializa o banco de dados e cria usuário admin se necessário."""
    with app.app_context():
        try:
            # Verifica se as tabelas já existem
            inspector = db.inspect(db.engine)
            tables_exist = inspector.get_table_names()
            
            if not tables_exist:
                print("Nenhuma tabela encontrada. Criando tabelas do banco de dados...")
                db.create_all()
                print("Tabelas criadas com sucesso!")
            else:
                print(f"Tabelas já existem no banco de dados: {', '.join(tables_exist)}")
            
            # Cria um usuário admin se não existir nenhum usuário
            try:
                user_count = User.query.count()
                if user_count == 0:
                    print("Nenhum usuário encontrado. Criando usuário admin...")
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
                else:
                    print(f"Já existem {user_count} usuários no banco de dados. Pulando criação do admin.")
            except Exception as e:
                db.session.rollback()
                print(f"Erro ao verificar/criar usuário admin: {e}")
                print("Continuando mesmo assim...")
        except Exception as e:
            print(f"Erro ao inicializar banco de dados: {e}")
            print("Continuando mesmo assim...")

# Inicializa o Cloudinary se as credenciais estiverem definidas
if os.environ.get('CLOUDINARY_CLOUD_NAME') or os.environ.get('CLOUDINARY_URL'):
    init_cloudinary()
    print("Cloudinary configurado para armazenamento de arquivos.")
else:
    print("Aviso: Credenciais do Cloudinary não encontradas. O armazenamento de arquivos utilizará o sistema de arquivos local.")

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