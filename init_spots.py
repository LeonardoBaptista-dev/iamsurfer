# init_spots.py
from app import app, db
from models import State, City, SurfSpot

def init_spots():
    """Adiciona dados de exemplo para Estados, Cidades e Picos"""
    with app.app_context():
        # Verificar se já existem dados
        if State.query.count() > 0:
            print("Já existem estados no banco de dados. Pulando inicialização.")
            return

        # Criar estados
        estados = [
            State(name="Santa Catarina", uf="SC"),
            State(name="São Paulo", uf="SP"),
            State(name="Rio de Janeiro", uf="RJ"),
            State(name="Paraná", uf="PR"),
            State(name="Rio Grande do Sul", uf="RS"),
            State(name="Bahia", uf="BA"),
            State(name="Pernambuco", uf="PE"),
            State(name="Ceará", uf="CE"),
            State(name="Rio Grande do Norte", uf="RN"),
            State(name="Alagoas", uf="AL"),
            State(name="Espírito Santo", uf="ES"),
        ]
        db.session.add_all(estados)
        db.session.commit()
        print(f"Criados {len(estados)} estados.")

        # Criar cidades
        sc = State.query.filter_by(uf="SC").first()
        sp = State.query.filter_by(uf="SP").first()
        rj = State.query.filter_by(uf="RJ").first()
        pr = State.query.filter_by(uf="PR").first()
        rs = State.query.filter_by(uf="RS").first()
        ba = State.query.filter_by(uf="BA").first()
        pe = State.query.filter_by(uf="PE").first()
        ce = State.query.filter_by(uf="CE").first()
        rn = State.query.filter_by(uf="RN").first()
        al = State.query.filter_by(uf="AL").first()
        es = State.query.filter_by(uf="ES").first()

        cidades = [
            # Santa Catarina
            City(name="Florianópolis", state=sc),
            City(name="Imbituba", state=sc),
            City(name="Garopaba", state=sc),
            City(name="Palhoça", state=sc),
            City(name="Governador Celso Ramos", state=sc),
            City(name="Bombinhas", state=sc),
            City(name="Balneário Camboriú", state=sc),
            City(name="Itajaí", state=sc),
            City(name="Penha", state=sc),
            City(name="Laguna", state=sc),
            
            # São Paulo
            City(name="Ubatuba", state=sp),
            City(name="São Sebastião", state=sp),
            City(name="Ilhabela", state=sp),
            City(name="Guarujá", state=sp),
            City(name="Santos", state=sp),
            City(name="Praia Grande", state=sp),
            City(name="Itanhaém", state=sp),
            City(name="Peruíbe", state=sp),
            City(name="Ilha Comprida", state=sp),
            
            # Rio de Janeiro
            City(name="Rio de Janeiro", state=rj),
            City(name="Saquarema", state=rj),
            City(name="Arraial do Cabo", state=rj),
            City(name="Cabo Frio", state=rj),
            City(name="Búzios", state=rj),
            City(name="Maricá", state=rj),
            City(name="Niterói", state=rj),
            City(name="Angra dos Reis", state=rj),
            City(name="Paraty", state=rj),
            
            # Paraná
            City(name="Guaratuba", state=pr),
            City(name="Matinhos", state=pr),
            City(name="Pontal do Paraná", state=pr),
            
            # Rio Grande do Sul
            City(name="Torres", state=rs),
            City(name="Tramandaí", state=rs),
            City(name="Capão da Canoa", state=rs),
            City(name="Cidreira", state=rs),
            
            # Bahia
            City(name="Salvador", state=ba),
            City(name="Itacaré", state=ba),
            City(name="Ilhéus", state=ba),
            City(name="Porto Seguro", state=ba),
            City(name="Caraíva", state=ba),
            
            # Pernambuco
            City(name="Recife", state=pe),
            City(name="Porto de Galinhas", state=pe),
            City(name="Fernando de Noronha", state=pe),
            
            # Ceará
            City(name="Fortaleza", state=ce),
            City(name="Jericoacoara", state=ce),
            City(name="Paracuru", state=ce),
            
            # Rio Grande do Norte
            City(name="Natal", state=rn),
            City(name="Pipa", state=rn),
            City(name="São Miguel do Gostoso", state=rn),
            
            # Alagoas
            City(name="Maceió", state=al),
            
            # Espírito Santo
            City(name="Guarapari", state=es),
            City(name="Vila Velha", state=es),
        ]
        db.session.add_all(cidades)
        db.session.commit()
        print(f"Criadas {len(cidades)} cidades.")

        # Referências para as cidades
        # Santa Catarina
        floripa = City.query.filter_by(name="Florianópolis").first()
        imbituba = City.query.filter_by(name="Imbituba").first()
        garopaba = City.query.filter_by(name="Garopaba").first()
        palhoca = City.query.filter_by(name="Palhoça").first()
        gov_celso_ramos = City.query.filter_by(name="Governador Celso Ramos").first()
        bombinhas = City.query.filter_by(name="Bombinhas").first()
        balneario_camboriu = City.query.filter_by(name="Balneário Camboriú").first()
        itajai = City.query.filter_by(name="Itajaí").first()
        penha = City.query.filter_by(name="Penha").first()
        laguna = City.query.filter_by(name="Laguna").first()
        
        # São Paulo
        ubatuba = City.query.filter_by(name="Ubatuba").first()
        sao_sebastiao = City.query.filter_by(name="São Sebastião").first()
        ilhabela = City.query.filter_by(name="Ilhabela").first()
        guaruja = City.query.filter_by(name="Guarujá").first()
        santos = City.query.filter_by(name="Santos").first()
        praia_grande = City.query.filter_by(name="Praia Grande").first()
        itanhaem = City.query.filter_by(name="Itanhaém").first()
        peruibe = City.query.filter_by(name="Peruíbe").first()
        ilha_comprida = City.query.filter_by(name="Ilha Comprida").first()
        
        # Rio de Janeiro
        rio = City.query.filter_by(name="Rio de Janeiro").first()
        saquarema = City.query.filter_by(name="Saquarema").first()
        arraial = City.query.filter_by(name="Arraial do Cabo").first()
        cabo_frio = City.query.filter_by(name="Cabo Frio").first()
        buzios = City.query.filter_by(name="Búzios").first()
        marica = City.query.filter_by(name="Maricá").first()
        niteroi = City.query.filter_by(name="Niterói").first()
        angra = City.query.filter_by(name="Angra dos Reis").first()
        paraty = City.query.filter_by(name="Paraty").first()
        
        # Outras cidades de outros estados
        guaratuba = City.query.filter_by(name="Guaratuba").first()
        matinhos = City.query.filter_by(name="Matinhos").first()
        pontal = City.query.filter_by(name="Pontal do Paraná").first()
        torres = City.query.filter_by(name="Torres").first()
        tramandai = City.query.filter_by(name="Tramandaí").first()
        capao = City.query.filter_by(name="Capão da Canoa").first()
        cidreira = City.query.filter_by(name="Cidreira").first()
        salvador = City.query.filter_by(name="Salvador").first()
        itacare = City.query.filter_by(name="Itacaré").first()
        ilheus = City.query.filter_by(name="Ilhéus").first()
        porto_seguro = City.query.filter_by(name="Porto Seguro").first()
        caraiva = City.query.filter_by(name="Caraíva").first()
        recife = City.query.filter_by(name="Recife").first()
        porto_galinhas = City.query.filter_by(name="Porto de Galinhas").first()
        noronha = City.query.filter_by(name="Fernando de Noronha").first()
        fortaleza = City.query.filter_by(name="Fortaleza").first()
        jeri = City.query.filter_by(name="Jericoacoara").first()
        paracuru = City.query.filter_by(name="Paracuru").first()
        natal = City.query.filter_by(name="Natal").first()
        pipa = City.query.filter_by(name="Pipa").first()
        sao_miguel = City.query.filter_by(name="São Miguel do Gostoso").first()
        maceio = City.query.filter_by(name="Maceió").first()
        guarapari = City.query.filter_by(name="Guarapari").first()
        vila_velha = City.query.filter_by(name="Vila Velha").first()

        # Criar picos
        picos = [
            # Santa Catarina - Florianópolis
            SurfSpot(
                name="Joaquina",
                city=floripa,
                description="Praia com ondas fortes, ideal para surfistas experientes. Palco de importantes campeonatos.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="Florianópolis, SC",
                slug="joaquina"
            ),
            SurfSpot(
                name="Mole",
                city=floripa,
                description="Praia com ondas consistentes e tubulares quando há swell de leste/sudeste.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="Florianópolis, SC",
                slug="mole"
            ),
            SurfSpot(
                name="Barra da Lagoa",
                city=floripa,
                description="Praia com ondas mais tranquilas, ideal para iniciantes e longboarders.",
                wave_type="Beach Break",
                difficulty_level="Iniciante/Intermediário",
                location="Florianópolis, SC",
                slug="barra-da-lagoa"
            ),
            SurfSpot(
                name="Campeche",
                city=floripa,
                description="Praia extensa com diferentes tipos de onda. Bom para todos os níveis.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="Florianópolis, SC",
                slug="campeche"
            ),
            SurfSpot(
                name="Santinho",
                city=floripa,
                description="Praia com ondas de qualidade quando há swell de leste.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Florianópolis, SC",
                slug="santinho"
            ),
            SurfSpot(
                name="Moçambique",
                city=floripa,
                description="Praia extensa com ondas fortes e tubulares.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="Florianópolis, SC",
                slug="mocambique"
            ),
            SurfSpot(
                name="Lagoinha",
                city=floripa,
                description="Praia com ondas mais tranquilas, bom para iniciantes.",
                wave_type="Beach Break",
                difficulty_level="Iniciante/Intermediário",
                location="Florianópolis, SC",
                slug="lagoinha"
            ),
            SurfSpot(
                name="Matadeiro",
                city=floripa,
                description="Praia pequena com ondas de qualidade quando há swell de sul.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Florianópolis, SC",
                slug="matadeiro"
            ),
            SurfSpot(
                name="Solidão",
                city=floripa,
                description="Praia mais isolada com ondas potentes.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="Florianópolis, SC",
                slug="solidao"
            ),
            
            # Santa Catarina - Outras cidades
            SurfSpot(
                name="Praia do Rosa - Norte",
                city=imbituba,
                description="Uma das praias mais bonitas do Brasil, com ondas de qualidade.",
                wave_type="Point Break",
                difficulty_level="Intermediário",
                location="Imbituba, SC",
                slug="rosa-norte"
            ),
            SurfSpot(
                name="Praia do Rosa - Sul",
                city=imbituba,
                description="Parte sul da Praia do Rosa, com ondas mais fortes.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="Imbituba, SC",
                slug="rosa-sul"
            ),
            SurfSpot(
                name="Ibiraquera",
                city=imbituba,
                description="Praia com lagoa e ondas boas para iniciantes e longboard.",
                wave_type="Beach Break",
                difficulty_level="Iniciante/Intermediário",
                location="Imbituba, SC",
                slug="ibiraquera"
            ),
            SurfSpot(
                name="Itapirubá",
                city=imbituba,
                description="Praia com ondas consistentes e menos crowd.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Imbituba, SC",
                slug="itapiruba"
            ),
            SurfSpot(
                name="Ribanceira",
                city=imbituba,
                description="Praia com ondas potentes quando há swell de sul/sudeste.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="Imbituba, SC",
                slug="ribanceira"
            ),
            SurfSpot(
                name="Silveira",
                city=garopaba,
                description="Point famoso por suas ondas tubulares. Direita clássica.",
                wave_type="Point Break",
                difficulty_level="Avançado",
                location="Garopaba, SC",
                slug="silveira"
            ),
            SurfSpot(
                name="Ferrugem",
                city=garopaba,
                description="Praia com ondas de qualidade e cenário paradisíaco.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Garopaba, SC",
                slug="ferrugem"
            ),
            SurfSpot(
                name="Barra de Ibiraquera",
                city=imbituba,
                description="Barra da lagoa com ondas perfeitas quando aberta.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Imbituba, SC",
                slug="barra-ibiraquera"
            ),
            SurfSpot(
                name="Guarda do Embaú",
                city=palhoca,
                description="Reserva mundial do surf com ondas de classe mundial.",
                wave_type="Point Break",
                difficulty_level="Intermediário/Avançado",
                location="Palhoça, SC",
                slug="guarda-do-embau"
            ),
            SurfSpot(
                name="Mariscal",
                city=bombinhas,
                description="Praia com ondas de qualidade e menos frequentada.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Bombinhas, SC",
                slug="mariscal"
            ),
            SurfSpot(
                name="Brava",
                city=balneario_camboriu,
                description="Praia com ondas consistentes e boa infraestrutura.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="Balneário Camboriú, SC",
                slug="brava-bc"
            ),
            
            # São Paulo
            SurfSpot(
                name="Itamambuca",
                city=ubatuba,
                description="Praia preservada com ondas consistentes. Palco de campeonatos.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Ubatuba, SP",
                slug="itamambuca"
            ),
            SurfSpot(
                name="Félix",
                city=ubatuba,
                description="Praia com ondas de qualidade quando há swell de sul.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="Ubatuba, SP",
                slug="felix"
            ),
            SurfSpot(
                name="Vermelha do Norte",
                city=ubatuba,
                description="Praia com ondas fortes e tubulares.",
                wave_type="Beach Break",
                difficulty_level="Avançado",
                location="Ubatuba, SP",
                slug="vermelha-do-norte"
            ),
            SurfSpot(
                name="Maresias",
                city=sao_sebastiao,
                description="Uma das praias mais famosas para o surf no litoral paulista.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="São Sebastião, SP",
                slug="maresias"
            ),
            SurfSpot(
                name="Camburi",
                city=sao_sebastiao,
                description="Praia com ondas tubulares e potentes.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="São Sebastião, SP",
                slug="camburi"
            ),
            SurfSpot(
                name="Juquehy",
                city=sao_sebastiao,
                description="Praia com ondas boas para todos os níveis.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="São Sebastião, SP",
                slug="juquehy"
            ),
            SurfSpot(
                name="Guaecá",
                city=sao_sebastiao,
                description="Praia com ondas de qualidade e menos crowd.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="São Sebastião, SP",
                slug="guaeca"
            ),
            SurfSpot(
                name="Castelhanos",
                city=ilhabela,
                description="Praia de difícil acesso com ondas de qualidade.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="Ilhabela, SP",
                slug="castelhanos"
            ),
            SurfSpot(
                name="Tombo",
                city=guaruja,
                description="Praia com ondas tubulares e fortes.",
                wave_type="Beach Break",
                difficulty_level="Avançado",
                location="Guarujá, SP",
                slug="tombo"
            ),
            SurfSpot(
                name="Enseada",
                city=guaruja,
                description="Praia com ondas mais tranquilas, ideal para iniciantes.",
                wave_type="Beach Break",
                difficulty_level="Iniciante",
                location="Guarujá, SP",
                slug="enseada"
            ),
            
            # Rio de Janeiro
            SurfSpot(
                name="Copacabana",
                city=rio,
                description="Praia urbana com ondas variáveis, dependendo das condições.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="Rio de Janeiro, RJ",
                slug="copacabana"
            ),
            SurfSpot(
                name="Arpoador",
                city=rio,
                description="Point clássico no Rio, com ondas de qualidade e crowd intenso.",
                wave_type="Point Break",
                difficulty_level="Intermediário",
                location="Rio de Janeiro, RJ",
                slug="arpoador"
            ),
            SurfSpot(
                name="Ipanema",
                city=rio,
                description="Praia famosa com ondas para todos os níveis.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="Rio de Janeiro, RJ",
                slug="ipanema"
            ),
            SurfSpot(
                name="Barra da Tijuca",
                city=rio,
                description="Praia extensa com diversos picos e condições variadas.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="Rio de Janeiro, RJ",
                slug="barra-da-tijuca"
            ),
            SurfSpot(
                name="Prainha",
                city=rio,
                description="Praia preservada com ondas de qualidade e cenário natural.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="Rio de Janeiro, RJ",
                slug="prainha"
            ),
            SurfSpot(
                name="Grumari",
                city=rio,
                description="Praia preservada com ondas consistentes.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Rio de Janeiro, RJ",
                slug="grumari"
            ),
            SurfSpot(
                name="Itacoatiara",
                city=niteroi,
                description="Praia com ondas potentes e tubulares. Uma das melhores do Rio.",
                wave_type="Beach Break",
                difficulty_level="Avançado",
                location="Niterói, RJ",
                slug="itacoatiara"
            ),
            SurfSpot(
                name="Itaúna",
                city=saquarema,
                description="Palco de etapas do Circuito Mundial. Ondas de classe mundial.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="Saquarema, RJ",
                slug="itauna"
            ),
            SurfSpot(
                name="Recreio",
                city=rio,
                description="Praia com diversos picos e condições variadas.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="Rio de Janeiro, RJ",
                slug="recreio"
            ),
            SurfSpot(
                name="Macumba",
                city=rio,
                description="Praia com ondas fortes e tubulares quando há swell.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="Rio de Janeiro, RJ",
                slug="macumba"
            ),
            
            # Nordeste - Bahia
            SurfSpot(
                name="Tiririca",
                city=itacare,
                description="Point famoso em Itacaré com ondas de qualidade.",
                wave_type="Point Break",
                difficulty_level="Intermediário",
                location="Itacaré, BA",
                slug="tiririca"
            ),
            SurfSpot(
                name="Jeribucaçu",
                city=itacare,
                description="Praia de difícil acesso com ondas perfeitas.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="Itacaré, BA",
                slug="jeribucacu"
            ),
            SurfSpot(
                name="Engenhoca",
                city=itacare,
                description="Praia com ondas tubulares e menos crowd.",
                wave_type="Point Break",
                difficulty_level="Intermediário/Avançado",
                location="Itacaré, BA",
                slug="engenhoca"
            ),
            SurfSpot(
                name="Boca da Barra",
                city=salvador,
                description="Point na capital baiana com ondas de qualidade.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Salvador, BA",
                slug="boca-da-barra"
            ),
            
            # Nordeste - Pernambuco
            SurfSpot(
                name="Cacimba do Padre",
                city=noronha,
                description="Um dos melhores tubos do Brasil. Palco de campeonatos.",
                wave_type="Reef Break",
                difficulty_level="Avançado",
                location="Fernando de Noronha, PE",
                slug="cacimba-do-padre"
            ),
            SurfSpot(
                name="Boldró",
                city=noronha,
                description="Praia com ondas de qualidade em Fernando de Noronha.",
                wave_type="Reef Break",
                difficulty_level="Intermediário/Avançado",
                location="Fernando de Noronha, PE",
                slug="boldro"
            ),
            SurfSpot(
                name="Maracaípe",
                city=porto_galinhas,
                description="Point famoso no litoral de Pernambuco.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Porto de Galinhas, PE",
                slug="maracaipe"
            ),
            
            # Nordeste - Ceará
            SurfSpot(
                name="Praia do Futuro",
                city=fortaleza,
                description="Praia urbana com ondas consistentes.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="Fortaleza, CE",
                slug="praia-do-futuro"
            ),
            SurfSpot(
                name="Preá",
                city=jeri,
                description="Praia com ventos constantes, ideal para kitesurf e windsurf.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="Jericoacoara, CE",
                slug="prea"
            ),
            SurfSpot(
                name="Lagoinha",
                city=paracuru,
                description="Praia com ondas de qualidade no Ceará.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Paracuru, CE",
                slug="lagoinha-ce"
            ),
            
            # Nordeste - Rio Grande do Norte
            SurfSpot(
                name="Ponta Negra",
                city=natal,
                description="Praia urbana com ondas para todos os níveis.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="Natal, RN",
                slug="ponta-negra"
            ),
            SurfSpot(
                name="Pipa - Madeiro",
                city=pipa,
                description="Praia com ondas de qualidade e cenário deslumbrante.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Pipa, RN",
                slug="madeiro"
            ),
            SurfSpot(
                name="Pipa - Centro",
                city=pipa,
                description="Point principal de Pipa com ondas para todos os níveis.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="Pipa, RN",
                slug="pipa-centro"
            ),
            
            # Sul - Paraná
            SurfSpot(
                name="Matinhos - Pico de Pedra",
                city=matinhos,
                description="Point break sobre pedras com ondas de qualidade.",
                wave_type="Point Break",
                difficulty_level="Intermediário/Avançado",
                location="Matinhos, PR",
                slug="pico-de-pedra"
            ),
            SurfSpot(
                name="Guaratuba",
                city=guaratuba,
                description="Praia com ondas consistentes no litoral paranaense.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Guaratuba, PR",
                slug="guaratuba"
            ),
            
            # Sul - Rio Grande do Sul
            SurfSpot(
                name="Praia Grande",
                city=torres,
                description="Praia com ondas potentes quando há swell de sul.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="Torres, RS",
                slug="praia-grande-rs"
            ),
            SurfSpot(
                name="Atlântida",
                city=tramandai,
                description="Praia com ondas para iniciantes e intermediários.",
                wave_type="Beach Break",
                difficulty_level="Iniciante/Intermediário",
                location="Tramandaí, RS",
                slug="atlantida"            ),
            SurfSpot(
                name="Capão da Canoa",
                city=capao,
                description="Praia com ondas consistentes no litoral gaúcho.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Capão da Canoa, RS",
                slug="capao-da-canoa"
            ),
            SurfSpot(
                name="Cidreira",
                city=cidreira,
                description="Praia com ondas fortes quando há swell de sul.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="Cidreira, RS",
                slug="cidreira"
            ),
            
            # Espírito Santo
            SurfSpot(
                name="Praia do Morro",
                city=guarapari,
                description="Praia urbana com ondas para todos os níveis.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="Guarapari, ES",
                slug="praia-do-morro"
            ),
            SurfSpot(
                name="Barra do Jucu",
                city=vila_velha,
                description="Point tradicional no Espírito Santo com ondas de qualidade.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Vila Velha, ES",
                slug="barra-do-jucu"
            ),
            
            # Mais picos em Santa Catarina
            SurfSpot(
                name="Pinheira",
                city=palhoca,
                description="Praia extensa com ondas de qualidade e menos crowd.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Palhoça, SC",
                slug="pinheira"
            ),
            SurfSpot(
                name="Praia da Vila",
                city=imbituba,
                description="Praia no centro de Imbituba com ondas de qualidade.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Imbituba, SC",
                slug="praia-da-vila"
            ),
            SurfSpot(
                name="Farol de Santa Marta",
                city=laguna,
                description="Praia com ondas potentes e cenário deslumbrante.",
                wave_type="Point Break",
                difficulty_level="Intermediário/Avançado",
                location="Laguna, SC",
                slug="farol-santa-marta"
            ),
            SurfSpot(
                name="Cardoso",
                city=laguna,
                description="Praia com ondas tubulares e potentes.",
                wave_type="Beach Break",
                difficulty_level="Avançado",
                location="Laguna, SC",
                slug="cardoso"
            ),
            SurfSpot(
                name="Galheta",
                city=floripa,
                description="Praia de naturismo com ondas de qualidade.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Florianópolis, SC",
                slug="galheta"
            ),
            SurfSpot(
                name="Praia Brava",
                city=floripa,
                description="Praia com ondas consistentes e boa infraestrutura.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Florianópolis, SC",
                slug="praia-brava"
            ),
            SurfSpot(
                name="Armação",
                city=floripa,
                description="Praia tradicional com ondas para todos os níveis.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="Florianópolis, SC",
                slug="armacao"
            ),
            SurfSpot(
                name="Gamboa",
                city=garopaba,
                description="Praia com ondas de qualidade e menos crowd.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Garopaba, SC",
                slug="gamboa"
            ),
            
            # Mais picos em São Paulo
            SurfSpot(
                name="Praia Grande",
                city=ubatuba,
                description="Praia extensa com diversos picos para todos os níveis.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="Ubatuba, SP",
                slug="praia-grande-ubatuba"
            ),
            SurfSpot(
                name="Tenório",
                city=ubatuba,
                description="Praia urbana com ondas para iniciantes e intermediários.",
                wave_type="Beach Break",
                difficulty_level="Iniciante/Intermediário",
                location="Ubatuba, SP",
                slug="tenorio"
            ),
            SurfSpot(
                name="Boracéia",
                city=sao_sebastiao,
                description="Praia com ondas consistentes e menos crowd.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="São Sebastião, SP",
                slug="boraceia"
            ),
            SurfSpot(
                name="Paúba",
                city=sao_sebastiao,
                description="Praia pequena com ondas de qualidade.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="São Sebastião, SP",
                slug="pauba"
            ),
            SurfSpot(
                name="Baleia",
                city=sao_sebastiao,
                description="Praia com ondas para todos os níveis.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="São Sebastião, SP",
                slug="baleia"
            ),
            SurfSpot(
                name="Barra do Una",
                city=sao_sebastiao,
                description="Praia com ondas de qualidade e cenário preservado.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="São Sebastião, SP",
                slug="barra-do-una"
            ),
            SurfSpot(
                name="Praia do Lázaro",
                city=ubatuba,
                description="Praia com ondas tranquilas, ideal para iniciantes.",
                wave_type="Beach Break",
                difficulty_level="Iniciante",
                location="Ubatuba, SP",
                slug="lazaro"
            ),
            SurfSpot(
                name="Praia do Félix",
                city=ubatuba,
                description="Praia com ondas de qualidade e menos crowd.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Ubatuba, SP",
                slug="felix-ubatuba"
            ),
            
            # Mais picos no Rio de Janeiro
            SurfSpot(
                name="Leme",
                city=rio,
                description="Extensão de Copacabana com ondas para iniciantes.",
                wave_type="Beach Break",
                difficulty_level="Iniciante",
                location="Rio de Janeiro, RJ",
                slug="leme"
            ),
            SurfSpot(
                name="Leblon",
                city=rio,
                description="Praia urbana com ondas para todos os níveis.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="Rio de Janeiro, RJ",
                slug="leblon"
            ),
            SurfSpot(
                name="Joatinga",
                city=rio,
                description="Praia escondida com ondas de qualidade.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="Rio de Janeiro, RJ",
                slug="joatinga"
            ),
            SurfSpot(
                name="Barra de Guaratiba",
                city=rio,
                description="Praia com ondas de qualidade e menos crowd.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Rio de Janeiro, RJ",
                slug="barra-de-guaratiba"
            ),
            SurfSpot(
                name="Praia do Peró",
                city=cabo_frio,
                description="Praia com ondas para todos os níveis.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="Cabo Frio, RJ",
                slug="pero"
            ),
            SurfSpot(
                name="Praia Grande",
                city=arraial,
                description="Praia com ondas de qualidade em Arraial do Cabo.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Arraial do Cabo, RJ",
                slug="praia-grande-arraial"
            ),
            SurfSpot(
                name="Geribá",
                city=buzios,
                description="Principal praia para surf em Búzios.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Búzios, RJ",
                slug="geriba"
            ),
            SurfSpot(
                name="Tucuns",
                city=buzios,
                description="Praia com ondas de qualidade e menos crowd em Búzios.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Búzios, RJ",
                slug="tucuns"
            ),
            SurfSpot(
                name="Saquarema - Barrinha",
                city=saquarema,
                description="Point com ondas tubulares próximo a Itaúna.",
                wave_type="Beach Break",
                difficulty_level="Intermediário/Avançado",
                location="Saquarema, RJ",
                slug="barrinha"
            ),
            SurfSpot(
                name="Saquarema - Vilatur",
                city=saquarema,
                description="Extensão da praia de Saquarema com boas ondas.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Saquarema, RJ",
                slug="vilatur"
            ),
            
            # Mais picos no Nordeste
            SurfSpot(
                name="Ponta de Serrambi",
                city=porto_galinhas,
                description="Point com ondas de qualidade no litoral pernambucano.",
                wave_type="Reef Break",
                difficulty_level="Intermediário/Avançado",
                location="Porto de Galinhas, PE",
                slug="serrambi"
            ),
            SurfSpot(
                name="Pontal de Maracaípe",
                city=porto_galinhas,
                description="Encontro do rio com o mar, formando ondas de qualidade.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Porto de Galinhas, PE",
                slug="pontal-maracaipe"
            ),
            SurfSpot(
                name="Praia do Francês",
                city=maceio,
                description="Principal ponto de surf em Alagoas.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Maceió, AL",
                slug="praia-do-frances"
            ),
            SurfSpot(
                name="Jericoacoara",
                city=jeri,
                description="Praia com ondas de qualidade e cenário deslumbrante.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Jericoacoara, CE",
                slug="jericoacoara"
            ),
            SurfSpot(
                name="Icaraizinho",
                city=jeri,
                description="Point com ondas de qualidade próximo a Jericoacoara.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Jericoacoara, CE",
                slug="icaraizinho"
            ),
            SurfSpot(
                name="Flecheiras",
                city=fortaleza,
                description="Praia com ondas de qualidade no Ceará.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Fortaleza, CE",
                slug="flecheiras"
            ),
            SurfSpot(
                name="Pipa - Sibaúma",
                city=pipa,
                description="Extensão da praia de Pipa com ondas de qualidade.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Pipa, RN",
                slug="sibauma"
            ),
            SurfSpot(
                name="São Miguel do Gostoso",
                city=sao_miguel,
                description="Destino em ascensão para surfistas no RN.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="São Miguel do Gostoso, RN",
                slug="sao-miguel-gostoso"
            ),
            SurfSpot(
                name="Ponta Negra - Morro do Careca",
                city=natal,
                description="Point clássico em Natal com ondas para todos os níveis.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="Natal, RN",
                slug="morro-do-careca"
            ),
            
            # Mais picos na Bahia
            SurfSpot(
                name="Itacarezinho",
                city=itacare,
                description="Praia paradisíaca com ondas de qualidade.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Itacaré, BA",
                slug="itacarezinho"
            ),
            SurfSpot(
                name="Praia do Forte",
                city=salvador,
                description="Praia com ondas para todos os níveis próximo a Salvador.",
                wave_type="Beach Break",
                difficulty_level="Todos os níveis",
                location="Salvador, BA",
                slug="praia-do-forte"
            ),
            SurfSpot(
                name="Stella Maris",
                city=salvador,
                description="Point tradicional em Salvador com ondas de qualidade.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Salvador, BA",
                slug="stella-maris"
            ),
            SurfSpot(
                name="Trancoso",
                city=porto_seguro,
                description="Praia com ondas de qualidade e cenário paradisíaco.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Porto Seguro, BA",
                slug="trancoso"
            ),
            SurfSpot(
                name="Caraíva",
                city=caraiva,
                description="Vilarejo rústico com ondas de qualidade.",
                wave_type="Beach Break",
                difficulty_level="Intermediário",
                location="Caraíva, BA",
                slug="caraiva"
            ),
        ]
        db.session.add_all(picos)
        db.session.commit()
        print(f"Criados {len(picos)} picos de surf.")

if __name__ == "__main__":
    init_spots()