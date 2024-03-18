from flask import app


@app.route('/')
def homepage():
    return 'Hi, surfers'

@app.route('/perfil')
def perfil():
    return "perfil do usuário"