"""Seed de dados de demonstração do IAmSurfer.

Cria 10 surfistas (com avatares reais), cobrindo todas as patentes (XP) e todos
os selos (fotógrafo/negócio/atleta/influencer), 13 picos reais de PR/SC/SP no
mapa, posts com fotos, reels, stories, follows, curtidas, comentários,
mensagens e caronas — tudo interligado pra testar a plataforma populada.

Uso:
    python seed_demo.py           # cria os dados (pula se já existir)
    python seed_demo.py --reset   # apaga os dados de demo e recria

Imagens/vídeos usam URLs externas (Unsplash/pravatar/sample mp4), então funciona
igual em dev (local) e produção (Cloudinary) — o filtro img_url repassa URLs http.
"""
import sys
from datetime import datetime, timedelta

from app import app
from extensions import db
from models import (User, Post, Comment, Like, Follow, Message, Spot, SurfSpot,
                    SurfTrip, TripParticipant, UserBadge, Story, Notification,
                    PhotoSession, SessionPhoto, PhotoPurchase, SpotPhotoNew,
                    Business, Coupon)

DEMO_PASSWORD = "surf1234"
SENTINEL = "marina.klein"  # se existir, já foi semeado

AV = lambda n: f"https://i.pravatar.cc/300?img={n}"
SURF = [
    "https://images.unsplash.com/photo-1502680390469-be75c86b636f?w=1080&q=80&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1455729552865-3658a5d39692?w=1080&q=80&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1505459668311-8dfac7952bf0?w=1080&q=80&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1531722569936-825d3dd91b15?w=1080&q=80&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1520962922320-2038eebab146?w=1080&q=80&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1509914398892-963f53e6e2f1?w=1080&q=80&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1473116763249-2faaef81ccda?w=1080&q=80&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1437622368342-7a3d73a34c8f?w=1080&q=80&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1502209524164-acea936639a2?w=1080&q=80&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1530870110042-98b2cb110834?w=1080&q=80&auto=format&fit=crop",
]
VIDEOS = [
    "https://download.samplelib.com/mp4/sample-10s.mp4",
    "https://download.samplelib.com/mp4/sample-5s.mp4",
    "https://media.w3.org/2010/05/sintel/trailer.mp4",
    "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4",
]

NOW = datetime.utcnow()

# (username, nome_exibicao, email, location, points, [selos], avatar_idx, bio)
USERS = [
    ("marina.klein", "Marina Klein", "marina@demo.iamsurfer.com", "Florianópolis, SC", 3200,
     ["influencer", "atleta"], 11, "🌊 Embaixadora & criadora de conteúdo. Floripa é base, o mundo é o lineup."),
    ("caio.ribeiro", "Caio Ribeiro", "caio@demo.iamsurfer.com", "Maresias, SP", 1850,
     ["atleta"], 12, "Atleta profissional. Tubo é vida. Maresias raiz 🤙"),
    ("tati.borges", "Tati Borges", "tati@demo.iamsurfer.com", "Garopaba, SC", 980,
     ["fotografo"], 47, "📸 Fotógrafa de surf na Silveira e Ferrugem. Congelo suas melhores ondas."),
    ("leo.andrade", "Léo Andrade", "leo.a@demo.iamsurfer.com", "Matinhos, PR", 760,
     [], 13, "Surfista de fim de semana virou todo dia. Litoral do Paraná no coração."),
    ("duda.santos", "Duda Santos", "duda@demo.iamsurfer.com", "Ubatuba, SP", 540,
     ["influencer"], 31, "Itamambuca é meu quintal 🌴 Compartilho rotina de surf trip."),
    ("pedro.alves", "Pedro Alves", "pedro@demo.iamsurfer.com", "Guarujá, SP", 380,
     ["empresario"], 14, "Dono da Escola de Surf Tombo 🏄 Aulas pra todos os níveis."),
    ("rafa.lima", "Rafa Lima", "rafa@demo.iamsurfer.com", "Imbituba, SC", 230,
     [], 33, "Aprendendo a ler o mar todo dia. Praia do Rosa é mágica."),
    ("bruna.costa", "Bruna Costa", "bruna@demo.iamsurfer.com", "Guaratuba, PR", 140,
     [], 48, "Comecei a surfar ano passado e não paro mais 💙"),
    ("theo.martins", "Theo Martins", "theo@demo.iamsurfer.com", "Florianópolis, SC", 70,
     [], 15, "Marola, espuma e muita vontade. Bora?"),
    ("manu.rocha", "Manu Rocha", "manu@demo.iamsurfer.com", "São Sebastião, SP", 30,
     [], 32, "Primeiros dropes em Camburi. Sigam a jornada!"),
]

# (nome, cidade, estado, lat, lng, bottom, wave, difficulty, crowd, descricao,
#  best_wind, best_swell, best_tide)
SPOTS = [
    ("Praia da Joaquina", "Florianópolis", "SC", -27.6281, -48.4490, "areia", "beach break",
     "intermediário", "alto", "Clássico de Floripa. Direitas e esquerdas com força, fundo de areia e ondas consistentes o ano todo.", "Norte", "Sul", "média"),
    ("Praia Mole", "Florianópolis", "SC", -27.6028, -48.4290, "areia", "beach break",
     "intermediário", "alto", "Praia bonita e badalada, ondas rápidas. Pega bem com swell de sul/sudeste.", "Noroeste", "Sudeste", "todas"),
    ("Praia do Santinho", "Florianópolis", "SC", -27.4520, -48.3870, "areia", "beach break",
     "intermediário", "médio", "Pico extenso no norte da ilha, vários peaks. Funciona em diversas condições.", "Oeste", "Sul", "média"),
    ("Praia da Silveira", "Garopaba", "SC", -28.0260, -48.6180, "areia", "beach break",
     "avançado", "médio", "Onda de qualidade em Garopaba, paredes longas quando entra swell de sul.", "Norte", "Sul", "baixa"),
    ("Praia do Rosa", "Imbituba", "SC", -28.1280, -48.6360, "areia", "beach break",
     "intermediário", "baixo", "Cenário paradisíaco, ondas boas nas pontas. Ótima pra surf trip tranquila.", "Noroeste", "Sul", "média"),
    ("Guarda do Embaú", "Palhoça", "SC", -27.8980, -48.5840, "areia", "rivermouth",
     "intermediário", "alto", "Desembocadura do rio com direitas longas. Patrimônio do surf catarinense.", "Norte", "Sul", "média"),
    ("Praia de Matinhos", "Matinhos", "PR", -25.8170, -48.5430, "areia", "beach break",
     "iniciante", "médio", "Principal pico do litoral do Paraná. Ondas amigáveis, ótimo pra aprender.", "Oeste", "Sudeste", "todas"),
    ("Praia Brava de Caiobá", "Matinhos", "PR", -25.8490, -48.5360, "areia", "beach break",
     "intermediário", "médio", "Mais exposta que Matinhos, pega mais tamanho com swell de sudeste.", "Noroeste", "Sudeste", "média"),
    ("Ilha do Mel - Praia de Fora", "Paranaguá", "PR", -25.5060, -48.3200, "areia", "beach break",
     "avançado", "baixo", "Onda remota e potente na Ilha do Mel, acesso só de barco. Vale a missão.", "Oeste", "Sul", "baixa"),
    ("Maresias", "São Sebastião", "SP", -23.7905, -45.5700, "areia", "beach break",
     "intermediário", "alto", "Reduto do surf paulista, berço de campeões. Ondas potentes e disputadas.", "Norte", "Sul", "média"),
    ("Itamambuca", "Ubatuba", "SP", -23.3905, -45.0260, "areia", "beach break",
     "intermediário", "médio", "Onda perfeita emoldurada por mata atlântica. Direitas e esquerdas de qualidade.", "Noroeste", "Sudeste", "média"),
    ("Praia do Tombo", "Guarujá", "SP", -23.9994, -46.2588, "areia", "beach break",
     "avançado", "médio", "Onda forte e tubular do Guarujá. Bandeira preta frequente — respeito ao mar.", "Norte", "Sul", "baixa"),
    ("Camburi", "São Sebastião", "SP", -23.7780, -45.4520, "areia", "beach break",
     "iniciante", "médio", "Praia tranquila do litoral norte, boa pra evoluir e pegar espuma.", "Oeste", "Sudeste", "todas"),
]


def reset():
    """Apaga dados de demo (usuários com email @demo.iamsurfer.com e o que criaram)."""
    demo_users = User.query.filter(User.email.like('%@demo.iamsurfer.com')).all()
    ids = [u.id for u in demo_users]
    if not ids:
        print("Nada de demo pra apagar.")
        return
    # Apaga dependências que não têm cascade garantido a partir do User
    Notification.query.filter(Notification.user_id.in_(ids) | Notification.related_user_id.in_(ids)).delete(synchronize_session=False)
    for t in SurfTrip.query.filter(SurfTrip.creator_id.in_(ids)).all():
        db.session.delete(t)
    TripParticipant.query.filter(TripParticipant.user_id.in_(ids)).delete(synchronize_session=False)
    Story.query.filter(Story.user_id.in_(ids)).delete(synchronize_session=False)
    PhotoPurchase.query.filter(PhotoPurchase.user_id.in_(ids)).delete(synchronize_session=False)
    for s in Spot.query.filter(Spot.created_by.in_(ids)).all():
        db.session.delete(s)  # cascata apaga sessões/fotos/negócios/cupons do pico
    for u in demo_users:
        db.session.delete(u)  # cascade apaga posts/comments/likes/messages/follows
    db.session.commit()
    print(f"Removidos {len(ids)} usuários de demo e seus dados.")


def seed():
    # 1) Usuários
    users = {}
    for uname, name, email, loc, pts, badges, av, bio in USERS:
        u = User(username=uname, email=email, location=loc, points=pts, bio=bio,
                 profile_image=AV(av), is_public=True,
                 joined_at=NOW - timedelta(days=120 - USERS.index(
                     next(x for x in USERS if x[0] == uname)) * 8))
        u.set_password(DEMO_PASSWORD)
        db.session.add(u)
        users[uname] = u
        for b in badges:
            db.session.add(UserBadge(user=u, type=b, status='active', granted_at=NOW))
    db.session.flush()
    ulist = list(users.values())
    print(f"  + {len(ulist)} usuários (senha de todos: {DEMO_PASSWORD})")

    # 2) Picos (Spot) aprovados, distribuídos entre os criadores
    spots = []
    for i, (name, city, st, lat, lng, bottom, wave, diff, crowd, desc, bw, bs, bt) in enumerate(SPOTS):
        creator = ulist[i % len(ulist)]
        s = Spot(name=name, description=desc, latitude=lat, longitude=lng,
                 address=f"{name}, {city} - {st}", city=city, state=st, country="Brasil",
                 bottom_type=bottom, wave_type=wave, difficulty=diff, crowd_level=crowd,
                 best_wind_direction=bw, best_swell_direction=bs, best_tide=bt,
                 status='approved', is_active=True, created_by=creator.id,
                 created_at=NOW - timedelta(days=60 - i), approved_at=NOW)
        db.session.add(s)
        spots.append(s)
    db.session.flush()
    print(f"  + {len(spots)} picos no mapa (PR/SC/SP)")

    # 3) Posts (com foto, alguns marcando pico)
    captions = [
        ("Sessão histórica hoje! Mar de sul entrando perfeito, paredes longas o dia todo. 🌊", 0),
        ("Clássico de domingo com a galera. Água quentinha e onda boa, o que mais pedir?", 1),
        ("Dropei a maior da minha vida nessa. Coração ainda acelerado! 🔥", 2),
        ("Treino de cutback até o sol descer. Evoluindo todo dia 🤙", 3),
        ("Amanhecer no pico, ninguém na água. Esses são os melhores momentos do surf.", 4),
        ("Swell chegou com força! Bandeira amarela mas valeu cada remada.", 5),
        ("Primeira vez surfando aqui e me apaixonei. Que lugar absurdo 😍", 6),
        ("Free surf relax depois do trampo. Mar de leste, ondinha divertida.", 7),
        ("Conexão completa! Bati a seção e saí na espuma gritando 🏄", 8),
        ("Dia de observar o mar e estudar a previsão. Amanhã promete!", 9),
        ("Aula com a galera iniciante hoje. Ver os alunos dropando não tem preço.", 1),
        ("Trip rápida no fim de semana. Vale cada km pra encontrar onda assim.", 3),
    ]
    posts = []
    for i, (text, img) in enumerate(captions):
        author = ulist[i % len(ulist)]
        spot = spots[i % len(spots)] if i % 2 == 0 else None
        p = Post(content=text, image_url=SURF[img], user_id=author.id,
                 post_type='regular', spot_id=(spot.id if spot else None),
                 created_at=NOW - timedelta(days=i // 2, hours=(i * 5) % 24))
        db.session.add(p)
        posts.append(p)
    db.session.flush()
    print(f"  + {len(posts)} posts com foto")

    # 4) Reels (vídeo vertical)
    reel_caps = [
        "Tubo limpo em câmera lenta 🎥 marca quem precisa ver isso!",
        "Sequência completa da melhor onda do dia. Som no talo 🔊",
        "Aéreo treinado virou realidade! Quase caí mas valeu 😂",
        "Drone capturou esse alinhamento perfeito de ondas. Surreal.",
    ]
    reels = []
    for i, cap in enumerate(reel_caps):
        author = ulist[(i * 2) % len(ulist)]
        r = Post(content=cap, video_url=VIDEOS[i % len(VIDEOS)], image_url=SURF[(i + 3) % len(SURF)],
                 user_id=author.id, post_type='reel',
                 created_at=NOW - timedelta(days=i, hours=2))
        db.session.add(r)
        reels.append(r)
    db.session.flush()
    print(f"  + {len(reels)} reels")

    # 5) Stories (expiram em 24h) — pra barra de stories aparecer
    for i in range(6):
        author = ulist[i]
        db.session.add(Story(user_id=author.id, media_url=SURF[(i + 1) % len(SURF)],
                             media_type='image', created_at=NOW - timedelta(hours=i + 1),
                             expires_at=NOW + timedelta(hours=23 - i)))
    print("  + 6 stories ativos")

    # 6) Follows — grafo denso (cada um segue 4-6 outros)
    import itertools
    fcount = 0
    for a, b in itertools.permutations(ulist, 2):
        # segue de forma determinística pra criar densidade sem ser todos-todos
        if (a.id + b.id) % 3 != 0 and abs(ulist.index(a) - ulist.index(b)) <= 5:
            if not a.is_following(b):
                db.session.add(Follow(follower_id=a.id, followed_id=b.id))
                fcount += 1
    db.session.flush()
    print(f"  + {fcount} relações de follow")

    # 7) Likes — vários por post
    lcount = 0
    for p in posts + reels:
        for j, u in enumerate(ulist):
            if (u.id * 7 + p.id) % 3 == 0 and u.id != p.user_id:
                db.session.add(Like(user_id=u.id, post_id=p.id,
                                    created_at=p.created_at + timedelta(hours=1)))
                lcount += 1
    print(f"  + {lcount} curtidas")

    # 8) Comentários
    comment_texts = ["Que onda absurda! 🔥", "Mandou bem demais!", "Bora marcar um surf?",
                     "Esse pico é o melhor 🤙", "Foto épica!", "Saudade de surfar aí 😍",
                     "Tá voando hein!", "Top demais, parabéns!"]
    ccount = 0
    for i, p in enumerate(posts):
        for k in range(i % 3):
            commenter = ulist[(i + k + 1) % len(ulist)]
            if commenter.id != p.user_id:
                db.session.add(Comment(content=comment_texts[(i + k) % len(comment_texts)],
                                       user_id=commenter.id, post_id=p.id,
                                       created_at=p.created_at + timedelta(hours=2 + k)))
                ccount += 1
    print(f"  + {ccount} comentários")

    # 9) Mensagens — conversas entre pares
    convo = [
        ("leo.andrade", "marina.klein", ["Oi Marina! Curto demais seu conteúdo 🙌", "Vai rolar surf em Floripa esse fim de semana?"]),
        ("marina.klein", "leo.andrade", ["Opa Léo! Valeu 💙", "Vai sim, sábado de manhã na Mole. Cola!"]),
        ("bruna.costa", "pedro.alves", ["Pedro, ainda tem vaga na aula de sábado?"]),
        ("pedro.alves", "bruna.costa", ["Tem sim Bruna! 9h no Tombo. Te espero 🏄"]),
        ("rafa.lima", "tati.borges", ["Tati, você fotografou na Silveira ontem?", "Acho que peguei uma boa, queria as fotos!"]),
        ("caio.ribeiro", "duda.santos", ["Duda, partiu trip pra Itamambuca semana que vem?"]),
    ]
    mcount = 0
    for i, (s, r, msgs) in enumerate(convo):
        for j, m in enumerate(msgs):
            db.session.add(Message(sender_id=users[s].id, recipient_id=users[r].id,
                                   content=m, read=(i % 2 == 0),
                                   timestamp=NOW - timedelta(days=2, hours=10 - i - j)))
            mcount += 1
    db.session.flush()
    print(f"  + {mcount} mensagens")

    # 10) Caronas (SurfTrips) com participantes
    trips_data = [
        ("leo.andrade", "Caravana pra Matinhos no sábado", "Curitiba, PR", -25.4284, -49.2733,
         "Praia de Matinhos", -25.8170, -48.5430, 3, 30.0, "Saveiro branca - placa final 7"),
        ("marina.klein", "Surf trip Floripa → Garopaba", "Florianópolis, SC", -27.5949, -48.5482,
         "Praia da Silveira", -28.0260, -48.6180, 2, 25.0, "Fiat Argo prata"),
        ("caio.ribeiro", "Strike em Maresias amanhã cedo", "São Paulo, SP", -23.5505, -46.6333,
         "Maresias", -23.7905, -45.5700, 3, 50.0, "HRV preta"),
        ("duda.santos", "Ubatuba no feriado, bora?", "São José dos Campos, SP", -23.2237, -45.9009,
         "Itamambuca", -23.3905, -45.0260, 4, 40.0, "Kombi laranja 🚐"),
    ]
    # Compatibilidade: em bancos legados surf_trip.destination_id é NOT NULL.
    # Usa um SurfSpot de fallback (o destino real vem de destination_text/coords).
    fallback_dest = SurfSpot.query.first()
    if fallback_dest is None:
        fallback_dest = SurfSpot(name='Destino', location='Brasil', slug='destino-demo')
        db.session.add(fallback_dest)
        db.session.flush()
    tcount = 0
    for i, (creator, title, dep, dlat, dlng, desttxt, tlat, tlng, seats, contrib, veh) in enumerate(trips_data):
        t = SurfTrip(title=title, creator_id=users[creator].id, departure_location=dep,
                     departure_lat=dlat, departure_lng=dlng, destination_id=fallback_dest.id,
                     destination_lat=tlat, destination_lng=tlng, destination_text=desttxt,
                     departure_time=NOW + timedelta(days=i + 2, hours=6),
                     return_time=NOW + timedelta(days=i + 2, hours=14),
                     available_seats=seats, contribution=contrib, vehicle_info=veh,
                     description="Bora dividir a estrada e a gasolina. Prancha vai no rack!",
                     status='Scheduled', created_at=NOW - timedelta(days=1))
        db.session.add(t)
        db.session.flush()
        # participantes
        riders = [u for u in ulist if u.id != users[creator].id][i:i + 2]
        for k, rider in enumerate(riders):
            db.session.add(TripParticipant(
                trip_id=t.id, user_id=rider.id,
                status='Confirmed' if k == 0 else 'Pending',
                message="Bora! Já tô dentro 🤙" if k == 0 else "Tem como me pegar no caminho?",
                meeting_lat=dlat + 0.01 * (k + 1), meeting_lng=dlng + 0.01 * (k + 1),
                meeting_label=f"Posto Shell da entrada ({rider.username})"))
        tcount += 1
    print(f"  + {tcount} caronas com participantes")

    # 11) Notificações pros usuários de demo (bell com contador)
    ncount = 0
    for i, u in enumerate(ulist):
        other = ulist[(i + 1) % len(ulist)]
        db.session.add(Notification(user_id=u.id, type='follow',
                                    content=f'{other.username} começou a te seguir',
                                    related_user_id=other.id, read=False,
                                    created_at=NOW - timedelta(hours=i + 1)))
        if posts:
            p = posts[i % len(posts)]
            db.session.add(Notification(user_id=u.id, type='like',
                                        content=f'{other.username} curtiu seu post',
                                        related_user_id=other.id, related_post_id=p.id,
                                        read=False, created_at=NOW - timedelta(hours=i + 2)))
        ncount += 2
    print(f"  + {ncount} notificações")

    # 12) Venda de fotos — APENAS fotógrafos (Tati) criam sessões e fotos
    tati = users['tati.borges']
    by_name = {s.name: s for s in spots}
    sess_imgs = ['sess1.jpg', 'sess2.jpg', 'sess3.jpg', 'sess4.jpg', 'sess5.jpg', 'sess6.jpg']
    photo_sessions_data = [
        (by_name['Praia da Silveira'], "Swell de Sul na Silveira", 25.0, sess_imgs[:3]),
        (by_name['Praia da Joaquina'], "Sunset session na Joaquina", 30.0, sess_imgs[3:]),
    ]
    all_session_photos = []
    for spot, title, price, imgs in photo_sessions_data:
        sess = PhotoSession(spot_id=spot.id, title=title,
                            description="Fotos em alta resolução. Compre a sua e leve a recordação da sessão!",
                            session_date=(NOW - timedelta(days=2)).date(),
                            photographer_id=tati.id, price_per_photo=price, is_active=True)
        db.session.add(sess)
        db.session.flush()
        for fn in imgs:
            sp = SessionPhoto(session_id=sess.id, filename=fn, title="Onda do dia", price=price, is_available=True)
            db.session.add(sp)
            all_session_photos.append(sp)
    db.session.flush()
    # Uma compra concretizada (prova que a venda funciona)
    if all_session_photos:
        buyer = users['rafa.lima']
        db.session.add(PhotoPurchase(photo_id=all_session_photos[0].id, user_id=buyer.id,
                                     amount_paid=all_session_photos[0].price, status='completed'))
    print(f"  + 2 sessões de fotos à venda ({len(all_session_photos)} fotos) — fotógrafa Tati")

    # Fotos de capa dos picos (também enviadas pela fotógrafa)
    for i, sname in enumerate(['Praia de Matinhos', 'Maresias', 'Praia da Joaquina']):
        db.session.add(SpotPhotoNew(spot_id=by_name[sname].id, filename=f'spot{i+1}.jpg',
                                    title=f'{sname} pela lente da Tati', uploaded_by=tati.id,
                                    is_cover=True))

    # 13) Negócios & cupons — APENAS empresários (Pedro)
    pedro = users['pedro.alves']
    biz_pousada = Business(owner_id=pedro.id, spot_id=by_name['Praia de Matinhos'].id,
                           name="Pousada Onda Sul", category="pousada",
                           description="Pousada pé na areia em Matinhos. Café da manhã regional, guarda-pranchas e aquecimento pós-surf.",
                           phone="(41) 99876-5432", instagram="@pousadaondasul",
                           address="Av. Atlântica, 1200 - Matinhos/PR")
    db.session.add(biz_pousada)
    db.session.flush()
    for code, disc, desc, days in [
        ("SURF10", "10%", "10% de desconto na diária para surfistas", 45),
        ("CAFE", "Grátis", "Café da manhã cortesia na primeira noite", 60),
        ("3X2", "3 por 2", "3 diárias pagando 2 na baixa temporada", 90),
    ]:
        db.session.add(Coupon(business_id=biz_pousada.id, code=code, discount=disc,
                              description=desc, valid_until=(NOW + timedelta(days=days)).date()))

    biz_escola = Business(owner_id=pedro.id, spot_id=by_name['Praia do Tombo'].id,
                          name="Escola de Surf Tombo", category="escola",
                          description="Aulas para todos os níveis, prancha e lycra inclusos. Instrutores certificados.",
                          phone="(13) 98123-4567", instagram="@escolasurftombo",
                          address="Praia do Tombo - Guarujá/SP")
    db.session.add(biz_escola)
    db.session.flush()
    db.session.add(Coupon(business_id=biz_escola.id, code="AULA15", discount="15%",
                          description="15% no pacote de 4 aulas", valid_until=(NOW + timedelta(days=30)).date()))
    print("  + 2 negócios (pousada em Matinhos + escola no Tombo) com 4 cupons — empresário Pedro")

    db.session.commit()
    print("\n[OK] Seed concluido com sucesso!")
    print(f"   Login de teste: qualquer usuario acima / senha: {DEMO_PASSWORD}")
    print(f"   Ex.: marina.klein / {DEMO_PASSWORD}")


if __name__ == '__main__':
    with app.app_context():
        if '--reset' in sys.argv:
            reset()
        if User.query.filter_by(username=SENTINEL).first():
            print(f"Já existe '{SENTINEL}'. Use --reset pra recriar. Saindo.")
            sys.exit(0)
        print("Semeando dados de demo...")
        seed()
