"""Normalização de nomes de estados brasileiros.

Aceita siglas (PR), nomes com/sem acento e variações de caixa
(parana, Parana, PARANÁ) e devolve sempre o nome canônico ("Paraná").
Usado para padronizar os estados dos picos (filtro do mapa e cadastro).
"""
import unicodedata

# Nome canônico de cada estado (com acento e caixa corretos)
CANONICAL_STATES = [
    'Acre', 'Alagoas', 'Amapá', 'Amazonas', 'Bahia', 'Ceará', 'Distrito Federal',
    'Espírito Santo', 'Goiás', 'Maranhão', 'Mato Grosso', 'Mato Grosso do Sul',
    'Minas Gerais', 'Pará', 'Paraíba', 'Paraná', 'Pernambuco', 'Piauí',
    'Rio de Janeiro', 'Rio Grande do Norte', 'Rio Grande do Sul', 'Rondônia',
    'Roraima', 'Santa Catarina', 'São Paulo', 'Sergipe', 'Tocantins',
]

# Sigla (UF) -> nome canônico
UF_TO_STATE = {
    'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas', 'BA': 'Bahia',
    'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo', 'GO': 'Goiás',
    'MA': 'Maranhão', 'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul',
    'MG': 'Minas Gerais', 'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná',
    'PE': 'Pernambuco', 'PI': 'Piauí', 'RJ': 'Rio de Janeiro',
    'RN': 'Rio Grande do Norte', 'RS': 'Rio Grande do Sul', 'RO': 'Rondônia',
    'RR': 'Roraima', 'SC': 'Santa Catarina', 'SP': 'São Paulo', 'SE': 'Sergipe',
    'TO': 'Tocantins',
}


def _strip(s):
    """minúsculas, sem acento e sem espaços nas pontas (chave de comparação)."""
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    return s.strip().lower()


# Chave normalizada (sem acento/caixa) -> nome canônico
_BY_NORM = {_strip(name): name for name in CANONICAL_STATES}


def normalize_state(value):
    """Devolve o nome canônico do estado. Se não reconhecer, devolve o original
    (apenas com as pontas aparadas) para não perder dados de estados/regiões
    estrangeiros."""
    if not value:
        return value
    v = value.strip()
    # Sigla de 2 letras (PR, SC, SP...)
    if len(v) == 2 and v.upper() in UF_TO_STATE:
        return UF_TO_STATE[v.upper()]
    # Nome por extenso (com qualquer acentuação/caixa)
    return _BY_NORM.get(_strip(v), v)
