"""Selos de papel (roles) do IAmSurfer e seus privilégios.

Diferente das patentes (gamificação por XP, em gamification.py), os selos são
concedidos (no v1, pelo admin) e desbloqueiam poderes específicos.
"""

BADGES = {
    'fotografo':  {'label': 'Fotógrafo',  'icon': 'bi-camera',
                   'desc': 'Cria sessões e vende fotos nos picos'},
    'empresario': {'label': 'Negócio',    'icon': 'bi-shop',
                   'desc': 'Divulga negócio e cupons dentro do pico'},
    'atleta':     {'label': 'Atleta',     'icon': 'bi-trophy',
                   'desc': 'Atleta / embaixador verificado'},
    'influencer': {'label': 'Influencer', 'icon': 'bi-star',
                   'desc': 'Criador de conteúdo verificado'},
}

# Ordem de exibição
ORDER = ['fotografo', 'empresario', 'atleta', 'influencer']


def info(role_type):
    """Dados de exibição de um selo (label, icon, desc) ou None."""
    return BADGES.get(role_type)
