# IAmSurfer

IAmSurfer é uma rede social para surfistas compartilharem experiências, fotos, dicas e se conectarem com outros amantes do surf.

## Funcionalidades

- **Registro e Autenticação de Usuários**: Crie uma conta, faça login e gerencie seu perfil.
- **Perfis de Usuário**: Personalize seu perfil com foto, biografia e localização.
- **Publicações**: Compartilhe suas experiências de surf com textos e imagens.
- **Sistema de Seguidores**: Siga outros surfistas e seja seguido.
- **Feed Personalizado**: Veja publicações de pessoas que você segue.
- **Comentários e Curtidas**: Interaja com as publicações de outros usuários.
- **Mensagens Diretas**: Comunique-se de forma privada com outros usuários.
- **Painel de Administração**: Gerencie usuários e conteúdo (apenas para administradores).

## Tecnologias Utilizadas

- **Backend**: Python, Flask
- **Banco de Dados**: SQLite (desenvolvimento), PostgreSQL (produção)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Contêinerização**: Docker, Docker Compose
- **Autenticação**: Flask-Login
- **ORM**: SQLAlchemy
- **Migrations**: Flask-Migrate

## Configuração do Ambiente de Desenvolvimento

### Utilizando Docker (Recomendado)

1. Certifique-se de ter Docker e Docker Compose instalados no seu sistema.

2. Clone o repositório:
   ```
   git clone https://github.com/seu-usuario/iamsurfer.git
   cd iamsurfer
   ```

3. Inicie os contêineres:
   ```
   docker compose up --build
   ```

4. Acesse a aplicação em `http://localhost:5001`.

### Configuração Local

1. Clone o repositório:
   ```
   git clone https://github.com/seu-usuario/iamsurfer.git
   cd iamsurfer
   ```

2. Crie e ative um ambiente virtual:
   ```
   python -m venv venv
   # No Windows
   venv\Scripts\activate
   # No Unix ou MacOS
   source venv/bin/activate
   ```

3. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

4. Configure as variáveis de ambiente:
   Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:
   ```
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=sua_chave_secreta
   DATABASE_URL=sqlite:///iamsurfer.db
   ```

5. Inicialize o banco de dados:
   ```
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

6. (Opcional) Crie dados de teste:
   ```
   python init_db.py
   ```

7. Execute a aplicação:
   ```
   flask run
   ```

8. Acesse a aplicação em `http://localhost:5000`.

## Estrutura do Projeto

```
iamsurfer/
│
├── app.py                    # Arquivo principal da aplicação
├── models.py                 # Definição dos modelos de dados
├── init_db.py                # Script para criar dados de teste
│
├── routes/                   # Rotas da aplicação
│   ├── admin.py              # Rotas de administração
│   ├── auth.py               # Rotas de autenticação
│   ├── main.py               # Rotas principais
│   ├── messages.py           # Rotas de mensagens
│   └── posts.py              # Rotas de publicações
│
├── static/                   # Arquivos estáticos
│   ├── css/                  # Estilos CSS
│   ├── js/                   # Scripts JavaScript
│   └── uploads/              # Uploads de imagens
│       ├── posts/            # Imagens de publicações
│       └── profile_pics/     # Fotos de perfil
│
├── templates/                # Templates HTML
│   ├── admin/                # Templates de administração
│   ├── auth/                 # Templates de autenticação
│   ├── main/                 # Templates principais
│   ├── messages/             # Templates de mensagens
│   └── posts/                # Templates de publicações
│
├── Dockerfile                # Configuração do Docker
├── docker-compose.yml        # Configuração do Docker Compose
└── requirements.txt          # Dependências do projeto
```

## Credenciais Padrão

Após inicializar a aplicação, um usuário administrador é criado automaticamente:
- **Usuário**: admin
- **Email**: admin@iamsurfer.com
- **Senha**: admin123

## Desenvolvimento

### Migrações do Banco de Dados

Para criar uma nova migração após alterar os modelos:

```
flask db migrate -m "Descrição da alteração"
flask db upgrade
```

### Adicionando Dados de Teste

Execute o script de inicialização para criar usuários e publicações de teste:

```
python init_db.py
```

## Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Faça commit das suas alterações (`git commit -m 'Adiciona nova feature'`)
4. Faça push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE). 