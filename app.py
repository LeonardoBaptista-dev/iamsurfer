from flask import Flask, Markup, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os
from dotenv import load_dotenv
import time
import re

from flask import url_for

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

# Configuração para desenvolvimento local vs produção
# No Docker, mesmo em desenvolvimento, vamos usar armazenamento local
USE_LOCAL_STORAGE = not is_production  # Use armazenamento local em desenvolvimento e Docker

# Imprime informação sobre o modo de armazenamento
print(f"🔧 Modo de armazenamento: {'LOCAL' if USE_LOCAL_STORAGE else 'CLOUDINARY'}")
print(f"🗄️ Database URL: {'PostgreSQL' if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] else 'SQLite'}")
print(f"🐳 Ambiente: {'DOCKER' if os.path.exists('/.dockerenv') else 'LOCAL'}")

# Certifica-se de que a pasta instance existe
os.makedirs(app.instance_path, exist_ok=True)

# Certifica-se de que as pastas de upload existem
upload_dirs = [
    os.path.join(app.root_path, 'static/uploads'),
    os.path.join(app.root_path, 'static/uploads/posts'),
    os.path.join(app.root_path, 'static/uploads/posts/thumbnail'),
    os.path.join(app.root_path, 'static/uploads/posts/small'),
    os.path.join(app.root_path, 'static/uploads/posts/medium'),
    os.path.join(app.root_path, 'static/uploads/posts/large'),
    os.path.join(app.root_path, 'static/uploads/posts/original'),
    os.path.join(app.root_path, 'static/uploads/profiles')
]
for dir_path in upload_dirs:
    os.makedirs(dir_path, exist_ok=True)

print(f"📁 Diretórios de upload criados: {len(upload_dirs)} pastas")

# Filtro personalizado para transformar quebras de linha em <br>
@app.template_filter('nl2br')
def nl2br(value):
    if value:
        return Markup(value.replace('\n', '<br>'))
    return value

# Filtro para processar URLs de imagem
@app.template_filter('img_url')
def img_url(path):
    if not path:
        return url_for('static', filename='uploads/default_profile.jpg')
    if 'cloudinary.com' in path or path.startswith('http://') or path.startswith('https://'):
        return path  # Retorna a URL externa diretamente
    return url_for('static', filename=path)  # Arquivo local

# Filtros para o novo sistema de imagens responsivas
@app.template_filter('responsive_img')
def responsive_img_filter(urls, alt="", css_class=""):
    """Gera tag img responsiva com srcset"""
    if USE_LOCAL_STORAGE:
        from local_image_processor import ResponsiveImageHelper
        if isinstance(urls, dict):
            return Markup(ResponsiveImageHelper.get_responsive_img_tag(urls, alt, css_class))
    else:
        from image_processor import ResponsiveImageHelper
        if isinstance(urls, dict):
            return Markup(ResponsiveImageHelper.get_responsive_img_tag(urls, alt, css_class))
    # Fallback para URLs simples
    return Markup(f'<img src="{img_url(urls)}" alt="{alt}" class="{css_class}" loading="lazy">')

@app.template_filter('thumbnail_url')
def thumbnail_url_filter(urls):
    """Retorna URL do thumbnail"""
    if USE_LOCAL_STORAGE:
        from local_image_processor import ResponsiveImageHelper
        if isinstance(urls, dict):
            return ResponsiveImageHelper.get_thumbnail_url(urls)
    else:
        from image_processor import ResponsiveImageHelper
        if isinstance(urls, dict):
            return ResponsiveImageHelper.get_thumbnail_url(urls)
    return img_url(urls)

@app.template_filter('feed_img_url')
def feed_img_url_filter(urls, is_mobile=False):
    """Retorna URL apropriada para feed"""
    if USE_LOCAL_STORAGE:
        from local_image_processor import ResponsiveImageHelper
        if isinstance(urls, dict):
            return ResponsiveImageHelper.get_feed_url(urls, is_mobile)
    else:
        from image_processor import ResponsiveImageHelper
        if isinstance(urls, dict):
            return ResponsiveImageHelper.get_feed_url(urls, is_mobile)
    return img_url(urls)

@app.template_filter('large_img_url')
def large_img_url_filter(urls):
    """Retorna URL da imagem grande"""
    if isinstance(urls, dict):
        if USE_LOCAL_STORAGE:
            return f"/static/{urls.get('large', urls.get('original', urls.get('medium', '')))}"
        else:
            return urls.get('large', urls.get('original', urls.get('medium', '')))
    return img_url(urls)

# Filtros específicos para imagens de perfil
@app.template_filter('profile_avatar')
def profile_avatar_filter(urls, alt="", css_class="rounded-circle", size="small"):
    """Gera tag img otimizada para avatares de perfil"""
    if USE_LOCAL_STORAGE:
        from local_image_processor import ResponsiveImageHelper
        if isinstance(urls, dict):
            return Markup(ResponsiveImageHelper.get_profile_avatar_tag(urls, alt, css_class, size))
    else:
        from image_processor import ResponsiveImageHelper
        if isinstance(urls, dict):
            return Markup(ResponsiveImageHelper.get_profile_avatar_tag(urls, alt, css_class, size))
    # Fallback para compatibilidade com o sistema antigo
    return Markup(f'<img src="{img_url(urls)}" alt="{alt}" class="{css_class}" loading="lazy">')

@app.template_filter('profile_thumbnail_url')
def profile_thumbnail_url_filter(urls):
    """Retorna URL do thumbnail de perfil (64x64)"""
    if USE_LOCAL_STORAGE:
        from local_image_processor import ResponsiveImageHelper
        if isinstance(urls, dict):
            return ResponsiveImageHelper.get_profile_thumbnail_url(urls)
    else:
        from image_processor import ResponsiveImageHelper
        if isinstance(urls, dict):
            return ResponsiveImageHelper.get_profile_thumbnail_url(urls)
    return img_url(urls)

@app.template_filter('profile_avatar_url')
def profile_avatar_url_filter(urls):
    """Retorna URL do avatar padrão de perfil (150x150)"""
    if USE_LOCAL_STORAGE:
        from local_image_processor import ResponsiveImageHelper
        if isinstance(urls, dict):
            return ResponsiveImageHelper.get_profile_avatar_url(urls)
    else:
        from image_processor import ResponsiveImageHelper
        if isinstance(urls, dict):
            return ResponsiveImageHelper.get_profile_avatar_url(urls)
    return img_url(urls)

@app.template_filter('profile_medium_url')
def profile_medium_url_filter(urls):
    """Retorna URL da imagem média de perfil (300x300)"""
    if USE_LOCAL_STORAGE:
        from local_image_processor import ResponsiveImageHelper
        if isinstance(urls, dict):
            return ResponsiveImageHelper.get_profile_medium_url(urls)
    else:
        from image_processor import ResponsiveImageHelper
        if isinstance(urls, dict):
            return ResponsiveImageHelper.get_profile_medium_url(urls)
    return img_url(urls)

@app.template_filter('profile_large_url')
def profile_large_url_filter(urls):
    """Retorna URL da imagem grande de perfil (600x600)"""
    if USE_LOCAL_STORAGE:
        from local_image_processor import ResponsiveImageHelper
        if isinstance(urls, dict):
            return ResponsiveImageHelper.get_profile_large_url(urls)
    else:
        from image_processor import ResponsiveImageHelper
        if isinstance(urls, dict):
            return ResponsiveImageHelper.get_profile_large_url(urls)
    return img_url(urls)

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
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'spots'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'sessions'), exist_ok=True)

# Importa os modelos após inicializar o db
@login_manager.user_loader
def load_user(user_id):
    from models import User
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

# Inicializa o banco de dados e cria dados necessários
def init_db():
    """Inicializa o banco de dados e cria usuário admin se necessário."""
    with app.app_context():
        try:
            # Verifica se as tabelas já existem
            inspector = db.inspect(db.engine)
            tables_exist = inspector.get_table_names()
            
            # Importa aqui para evitar importação circular
            from models import User, SurfSpot, SurfTrip, TripParticipant, Spot, SpotPhotoNew, PhotoSession, SessionPhoto, PhotoPurchase, SpotReport
            
            # Cria todas as tabelas se não existirem
            if not tables_exist or 'surf_trip' not in tables_exist:
                print("Criando ou atualizando tabelas no banco de dados...")
                db.create_all()
                print("Tabelas criadas ou atualizadas com sucesso!")
            else:
                print(f"Tabelas já existem no banco de dados: {', '.join(tables_exist)}")
            
            # Verifica se tabelas específicas existem e cria individualmente se necessário
            if 'surf_spot' not in tables_exist:
                print("Criando tabela surf_spot...")
                db.metadata.tables['surf_spot'].create(db.engine, checkfirst=True)
            
            if 'surf_trip' not in tables_exist:
                print("Criando tabela surf_trip...")
                db.metadata.tables['surf_trip'].create(db.engine, checkfirst=True)
                
            if 'trip_participant' not in tables_exist:
                print("Criando tabela trip_participant...")
                db.metadata.tables['trip_participant'].create(db.engine, checkfirst=True)
            
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
                
                # Adicionar spots de surf iniciais
                surf_spots_count = SurfSpot.query.count()
                if surf_spots_count == 0:
                    print("Criando spots de surf iniciais...")
                    surf_spots = [
                        SurfSpot(name="Campeche", location="Florianópolis, SC", slug="campeche"),
                        SurfSpot(name="Joaquina", location="Florianópolis, SC", slug="joaquina"),
                        SurfSpot(name="Praia do Rosa", location="Imbituba, SC", slug="rosa-norte"),
                        SurfSpot(name="Silveira", location="Garopaba, SC", slug="silveira"),
                        SurfSpot(name="Itamambuca", location="Ubatuba, SP", slug="itamambuca"),
                        SurfSpot(name="Praia da Vila", location="Imbituba, SC", slug="praia-da-vila"),
                        SurfSpot(name="Pico de Matinhos", location="Matinhos, PR", slug="pico-de-matinhos")
                    ]
                    db.session.add_all(surf_spots)
                    db.session.commit()
                    print(f"Criados {len(surf_spots)} spots de surf com sucesso!")
                else:
                    print(f"Já existem {surf_spots_count} spots de surf no banco de dados. Pulando criação.")
                
            except Exception as e:
                db.session.rollback()
                print(f"Erro ao verificar/criar dados iniciais: {e}")
                print("Continuando mesmo assim...")
        except Exception as e:
            print(f"Erro ao inicializar banco de dados: {e}")
            print("Continuando mesmo assim...")

# Inicializa o Cloudinary se as credenciais estiverem definidas

print("Armazenamento de arquivos configurado para uso local.")

# Importa e registra os blueprints
from routes.auth import auth
from routes.main import main
from routes.posts import posts
from routes.admin import admin
from routes.messages import messages

# Registra os blueprints
app.register_blueprint(auth)
app.register_blueprint(main)
app.register_blueprint(posts)
app.register_blueprint(admin)
app.register_blueprint(messages)

# Deve ser importado depois de inicializar os outros modelos
from routes.trips import trips
app.register_blueprint(trips)

# No final do arquivo, após os outros blueprints
from routes.spots import spots
app.register_blueprint(spots)

if __name__ == '__main__':
    if wait_for_db():
        init_db()
        app.run(debug=True, host='0.0.0.0')
else:
    # Para quando estiver rodando com Flask CLI (gunicorn, etc)
    wait_for_db()
    init_db()