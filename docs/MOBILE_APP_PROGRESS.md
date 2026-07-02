# IAmSurfer Mobile — Estado da Implementação (handoff)

> **Para a próxima sessão.** Leia este arquivo primeiro. Ele resume o que estamos
> construindo, o que já está pronto e funcionando, as decisões/armadilhas do
> ambiente, e o próximo passo concreto.
>
> Última atualização: **2026-06-30**.

---

## 1. O que estamos construindo

App mobile **nativo iOS + Android** do IAmSurfer (rede social de surf), com
**paridade com a web**. Plano-mestre detalhado (prompts A0–A13 backend, B0–B13
app): [`MOBILE_APP_IMPLEMENTATION.md`](./MOBILE_APP_IMPLEMENTATION.md).

**Arquitetura:** o backend Flask existente (site Jinja) ganha uma **API REST
`/api/v1`** (blueprint novo, JWT) que **reaproveita os mesmos models/DB/
Cloudinary** sem alterar o site. O app **Expo/React Native** (repo separado
`iamsurfer-app/`) consome essa API.

```
iamsurfer/        ← backend Flask (site Jinja + API REST /api/v1)  [git repo]
iamsurfer-app/    ← app Expo/React Native (TypeScript)             [git repo]
```

---

## 2. O que JÁ está pronto e verificado ✅

### Backend — Prompt A0 (fundação da API) + A1 (auth)
Pasta nova: **`iamsurfer/routes/api/`**
- `__init__.py` — blueprint `/api/v1`, init de JWT/CORS/rate-limit, `register_api(app)`, `GET /api/v1/ping`.
- `errors.py` — formato de erro único `{"error":{"code","message","fields"}}` + handlers (401/403/404/422/429/500) e classe `ApiError`.
- `pagination.py` — paginação **cursor-based** (`?cursor=&limit=`) → `{items, next_cursor}`.
- `serializers.py` — `user_full(viewer)`, `me_full`, `user_brief` (contrato da seção 2 do plano: `patente`, `counts`, `viewer_state`, URLs de mídia absolutas).
- `deps.py` — `current_api_user()`, `issue_tokens()`, `revoke_token()`, `body()`, `require_fields()`.
- `auth.py` — `POST /auth/register`, `/auth/login` (email **ou** username, case-insensitive), `/auth/refresh` (rotativo), `/auth/logout`, `GET /auth/me`, `POST /auth/push-token`.

Outras mudanças no backend:
- `models.py` — **+`TokenBlocklist`** (refresh revogados) e **+`DeviceToken`** (Expo push token por device).
- `migrations/versions/e3f4a5b6c7d8_*.py` — migration das 2 tabelas (down_revision = `d2b3c4e5f6a7`, que é o head).
- `app.py` — chama `register_api(app)` após registrar os blueprints do site.
- `requirements.txt` — `Flask-JWT-Extended==4.5.3`, `Flask-Cors==3.0.10`, `Flask-Limiter==2.8.1`.
- `.env.example` — `JWT_SECRET_KEY`, `API_CORS_ORIGINS`.
- `tests/conftest.py` + `tests/test_api_auth.py` — **8 testes passando** (ping, 401 padrão, fluxo register→login→refresh→me→logout, rotação/revogação, validação, push-token upsert).

**Como rodar os testes do backend:**
```bash
cd iamsurfer
python -m pytest tests/test_api_auth.py -q
```
Smoke: `python app.py` sobe site + API juntos (109 rotas; `/api/v1/ping` responde `{"ok":true,"version":"1"}`).

### App — Prompt B0 (scaffold + design system) + B1 (cliente/auth) + B2 (telas auth)
Pasta nova: **`iamsurfer-app/`** (Expo SDK 56, expo-router, React 19, RN 0.85).
- `src/theme/index.ts` — design system da marca (indigo `#3730a3`, spacing, tipografia).
- `src/components/` — `Button`, `Input`, `Avatar`, `Placeholder`.
- `src/api/client.ts` — fetch + `Authorization: Bearer` + **interceptor de refresh** (401 → refresh single-flight → retry → senão `onSessionExpired`); mapeia erro padrão p/ `ApiError`. `types.ts`, `auth.ts`.
- `src/lib/storage.ts` — tokens no **SecureStore**. `queryClient.ts` (React Query). `push.ts` (Expo push token).
- `src/context/AuthContext.tsx` — `signIn/register/signOut/refreshMe`, restaura sessão no boot, liga o `onSessionExpired`.
- `app/_layout.tsx` — provedores globais + **gate de autenticação** (logado→tabs, deslogado→login).
- `app/(auth)/login.tsx`, `signup.tsx` — telas com validação e erros da API.
- `app/(tabs)/_layout.tsx` + telas — bottom tabs **Início · Explorar · Criar · Reels · Perfil** (espelha o navbar web). `index` (feed placeholder + status da API), `profile` (perfil real do usuário logado + logout), demais placeholders.

**Verificado:** `npx tsc --noEmit` limpo **e** `npx expo export --platform android` gera o bundle Hermes com sucesso (rotas, imports e auth compilam para alvo nativo).

**Como rodar o app:**
```bash
cd iamsurfer-app
# copie .env.example -> .env e ajuste EXPO_PUBLIC_API_URL
npm install
npm start            # Expo Go / emulador
npm run typecheck    # tsc --noEmit
```
Detalhes no [`iamsurfer-app/README.md`](../../iamsurfer-app/README.md).

---

## 3. Armadilhas do ambiente (IMPORTANTE) ⚠️

- **NÃO subir o Flask para 3.x.** O site usa `from flask import Markup` e
  `from werkzeug.urls import url_parse`, removidos no Flask 2.3+/3. Manter
  **Flask 2.0.1 / Werkzeug 2.0.1**. (O `pip install` das libs novas chega a
  puxar Flask 3 — se acontecer, reinstale: `pip install "Flask==2.0.1"
  "Werkzeug==2.0.1" "itsdangerous==2.0.1"`.)
- O ambiente Python desta máquina não tinha as deps do projeto instaladas; foram
  instaladas Flask-SQLAlchemy 2.5.1, Flask-Login 0.5.0, Flask-Migrate 3.1.0,
  SQLAlchemy 1.4.46, etc. (compatíveis com Flask 2.0.1).
- **Disco:** C: vive quase cheio. Caches/temp já redirecionados para D: e
  **Docker movido para `D:\DockerData`** (junction). Ver memória `disk-constraint`.
  Builds pesados (EAS) → manter saída em D:.
- App em **Expo SDK 56 / React 19 / RN 0.85** (bleeding edge). `babel-preset-expo`
  já injeta o plugin do Reanimated/Worklets — **não** adicionar manualmente no
  `babel.config.js`. Instalações usaram `--legacy-peer-deps` quando deu ERESOLVE.

---

### Prompt A11 (upload assinado) + A2 (usuários/follow) — backend ✅
- `routes/api/media.py` — `POST /media/sign` (assinatura Cloudinary, folder confinada a `iamsurfer/`, 503 se Cloudinary off) e `POST /media/confirm`.
- `routes/api/users.py` — `GET /users/:u` (+counts/viewer_state), `/posts` (cursor, respeita `is_public`), `/followers`, `/following`, `POST|DELETE /users/:u/follow` (idempotente, XP+notificação, sem self/admin), `GET/PATCH /me`, `PATCH /me/avatar`, `GET /search/users`.
- `serializers.py` — `post_card`, `post_media`, `can_view_content` (privacidade).
- Testes: `tests/test_api_users.py` (10) + `tests/test_api_media.py` (6). **Suíte API: 24 passando.**

> Obs.: o **A7 (picos/SurfMap)** também já está no backend (`routes/api/spots.py`,
> `br_states.py`, `tests/test_api_spots.py`) — feito em paralelo.

### Prompt B6 (perfil + follow) — app ✅
- `src/api/users.ts`, `src/api/media.ts` (`uploadMedia` direto pro Cloudinary).
- `src/hooks/useProfile.ts` — `useProfile`, `useUserPosts` (infinite), `useFollowToggle` (otimista).
- `src/components/ProfileHeader.tsx`, `PostGrid.tsx`.
- `app/user/[username].tsx` — perfil de terceiros, follow/unfollow, bloqueio de perfil privado.
- `app/edit-profile.tsx` — avatar (expo-image-picker → upload assinado), bio, localização, privacidade.
- `app/search.tsx` — busca de surfistas → perfil. Aba **Perfil** com grid de posts.
- **Aba Explorar reservada para Picos (B8)** — só tem atalho de busca por ora.
- `app/_layout.tsx` agora é **Stack** (rotas user/edit/search com header). `tsc` limpo, bundle Android OK.

### Prompt A3 (feed/posts/likes/comentários) — backend ✅
- `routes/api/posts.py` — `GET /feed` (segue+próprios, cursor), `GET /explore` (públicos), `GET /posts/:id` (respeita privacidade), `POST /posts` (texto + media[] do Cloudinary + spot), `DELETE /posts/:id`, `POST|DELETE /posts/:id/like` (idempotente, XP+notificação), `GET|POST /posts/:id/comments`, `DELETE /comments/:id`.
- `serializers.py` — `comment_card`.
- Testes: `tests/test_api_posts.py` (10). **Suíte API total agora: 34.**

### Prompt B3 (feed + post + criar post) — app ✅
- `src/api/posts.ts`, `src/hooks/useFeed.ts`, `src/lib/time.ts` (timeAgo pt-BR).
- `src/components/PostCardView.tsx` — card com **like otimista**, mídia, contadores.
- `app/(tabs)/index.tsx` — feed infinito + pull-to-refresh + estados vazio/erro.
- `app/(tabs)/create.tsx` — criar post (foto/vídeo via expo-image-picker → upload assinado → cria → invalida feed).
- `app/post/[id].tsx` — detalhe + comentários (lista + enviar).

### A7 (picos) + telas de picos — feito pelo build paralelo ✅
- Backend `routes/api/spots.py` e app: aba **Explorar = SurfMap** (lista/busca),
  `app/spot/[id].tsx`, `app/spot/new.tsx`, `src/hooks/useSpots.ts`,
  `src/api/spots.ts`, tipos `Spot`/`SpotBrief`. Integra com o resto (bundle OK).

> **Estado app:** `tsc` limpo e **bundle Android OK** com tudo junto
> (auth, perfil/follow, feed/posts, criar, picos). Abas: Início (feed) ·
> Explorar (picos) · Criar · Reels (placeholder) · Perfil.

### Prompt A10 (ranking/badges) + B11 — ✅
- Backend `routes/api/ranking.py` — `GET /ranking` (offset/limit + `my_rank`), `GET /users/:u/badges`. Testes `test_api_ranking.py` (5).
- App: `src/api/ranking.ts`, `hooks/useRanking.ts`, `app/ranking.tsx` (pódio + minha posição), selos no `ProfileHeader`, atalho na aba Perfil.

### Prompt A5 (reels) + B5 — ✅
- Backend `routes/api/reels.py` — `GET /reels` (cursor, públicos), `POST /reels` (exige vídeo). Like/comentário reusam os endpoints de posts. Testes `test_api_reels.py` (4).
- App: `src/api/reels.ts`, `hooks/useReels.ts`, `app/(tabs)/reels.tsx` (pager vertical full-screen, autoplay no item visível via `expo-video`, mute ao tocar, like otimista, pausa ao sair da aba). Criar post agora tem toggle **"Publicar como Reel"** quando o vídeo é escolhido. Dep: `expo-video@56.1.4`.

### Prompt A4 (stories) + B4 — ✅
- Backend `routes/api/stories.py` — `GET /stories` (story bar agrupada, eu primeiro), `POST /stories` (mídia Cloudinary, expira 24h), `POST /stories/:id/seen` (idempotente), `DELETE /stories/:id`. Testes `test_api_stories.py` (5).
- App: `src/api/stories.ts`, `hooks/useStories.ts`, `components/StoryBar.tsx` (topo do feed, anel visto/não-visto, adicionar story), `app/stories/[userId].tsx` (viewer full-screen: barras de progresso, toque avança/volta, autoplay imagem/vídeo, marca visto, apagar próprio).

### Prompts A6+A12 (mensagens+push), A8 (caronas), A9 (fotos+pagamento) — backend ✅ (subagentes)
Construídos em paralelo por subagentes e integrados (blueprints registrados em `routes/api/__init__.py`):
- **A6/A12** `routes/api/messages.py` + `push.py` — `GET /conversations` (inbox), `GET/POST /conversations/:username[/messages]`, `GET /notifications`, `POST /notifications/read`, `GET /notifications/count`. Serviço Expo Push em lote (remove token morto `DeviceNotRegistered`), disparado no envio de mensagem. Testes (14).
- **A8** `routes/api/trips.py` — `GET/POST /trips`, `GET /trips/:id`, `POST /trips/:id/join|leave` (idempotente, lotação, XP), `GET /me/trips`. Testes (11).
- **A9** `routes/api/photos.py` + `payments.py` — `GET /photo-sessions[/:id]`, `POST /photos/:id/purchase`, `POST /webhooks/payments` (idempotente), `GET /me/purchases`. Preço sempre no servidor; foto só liberada após pago; **Mercado Pago** (Pix+cartão) com modo-teste quando não há credencial. +3 colunas em `PhotoPurchase` (migration `f4a5b6c7d8e9`). Envs: `MERCADOPAGO_ACCESS_TOKEN` etc. Testes (9).

### B7 (push — recebimento) parcial no app ✅
- `src/lib/notifications.ts` — handler de foreground + deep-link ao tocar (like/comentário→post, follow→perfil, mensagem→conversa). Ligado no `_layout`.
- Correções de config (expo-doctor): `expo-font` instalado, `splash` migrado para o plugin `expo-splash-screen`, navegação com becos sem saída resolvidos (pico do post e grades de perfil agora abrem a tela certa).

### Telas B7 (mensagens/notificações), B9 (caronas), B10 (fotos/checkout) — app ✅ (subagentes + integração)
Construídas em paralelo por 3 subagentes (cada uma lendo o contrato real no backend) e **integradas** por mim:
- **B7** `src/api/messages.ts` + `hooks/useMessages.ts` + `app/messages/index.tsx` (inbox), `app/messages/[username].tsx` (chat, FlatList inverted + KeyboardAvoiding), `app/notifications.tsx` (marca lidas ao abrir; toca → perfil/conversa).
- **B9** `src/api/trips.ts` + `hooks/useTrips.ts` + `app/trips/index.tsx` (lista/busca + "minhas caronas" + FAB), `app/trips/[id].tsx` (detalhe, participar/sair otimista, trata lotação), `app/trips/new.tsx` (criar).
- **B10** `src/api/photos.ts` + `hooks/usePhotos.ts` + `lib/money.ts` + `app/photos/index.tsx` (vitrine), `app/photos/[id].tsx` (grade com preview/marca d'água), `app/photos/checkout.tsx` (Mercado Pago via `expo-web-browser` + Pix + "simular pagamento" no modo-teste + polling até pago), `app/purchases.tsx` (minhas compras + download). Dep nova: `expo-web-browser`.
- **Integração:** 10 rotas registradas no `_layout.tsx`; header do feed com **ícones de notificações (badge de não-lidas) + mensagens**; **Reels full-screen** (sem header); menu no Perfil com **Caronas · Fotos à venda · Minhas compras**. `tsc` limpo + **bundle Android OK (4.6MB)**.

### Prompt B13 (build + publicação) — ✅ config / ⚠️ passos manuais
- `eas.json` — perfis `development`/`preview`/`production` (+ `EXPO_PUBLIC_API_URL` por perfil apontando pra API de produção; `submit` com placeholders Apple/Google).
- `app.json` — `runtimeVersion` (appVersion), `ios.buildNumber`, `android.versionCode`, bundle ids/permissões/ícone/splash já prontos.
- `.gitignore` — segredos de publicação (service account, keystore, .p8/.p12, .env).
- `docs/BUILD_AND_PUBLISH.md` — runbook completo (login/init, arte final, build preview/produção, submit TestFlight/Internal, metadados, conta demo do revisor, OTA).
- **Falta (manual, seu):** `eas login`+`eas init`, arte final nos `assets/`, **deploy do backend `/api/v1` em produção**, contas **Apple ($99/ano)** e **Google ($25)**, rodar `eas build`/`eas submit`.

### Prompt B12 (shell de navegação + resiliência) — ✅
- **Offline:** `src/lib/network.ts` liga NetInfo ao `onlineManager` do React Query (pausa queries sem conexão) e AppState ao `focusManager` (refetch ao voltar pro foreground); `src/components/OfflineBanner.tsx` (faixa "sem conexão" global no `_layout`). Dep: `@react-native-community/netinfo`.
- **ErrorBoundary** global exportado no `_layout` (sem tela branca em erro de render).
- **Shell:** tabs definitivos + header do feed com notificações(badge)/mensagens + menus no perfil (já integrados). Deep links por esquema `iamsurfer://` funcionam.
- **Universal links (https):** adiados para B13 — exigem domínio estável (o de produção hoje é um host efêmero `sslip.io`); documentado como pré-requisito.

### Correção de roteamento — ✅
- `app/index.tsx` decide o destino por auth (deslogado → login) em vez de sempre `/(tabs)` — evitava corrida e um 401 no feed para quem não está logado.

---

## Checklist de progresso

**Backend:** ✅A0 ✅A1 ✅A2 ✅A3 ✅A4 ✅A5 ✅A6 ✅A7 ✅A8 ✅A9 ✅A10 ✅A11 ✅A12 ✅A13 — **completo**
**App:** ✅B0 ✅B1 ✅B2 ✅B3 ✅B4 ✅B5 ✅B6 ✅B7 ✅B8 ✅B9 ✅B10 ✅B11 ✅B12 · ✅B13 config (⚠️ build/submit manual: contas Apple/Google)

**TODAS as features estão implementadas.** Só resta a execução manual da publicação (B13): contas pagas, arte final, deploy do backend e rodar `eas build`/`eas submit`.

**Suíte de testes backend: 93** (86 + 7 de contrato) (auth 8 · users 10 · media 6 · posts 10 · spots 4 · ranking 5 · reels 4 · stories 5 · messages 14 · trips 11 · photos 9). App: `tsc` limpo + **bundle Android OK (4.6MB)**.

**Todas as features do app estão implementadas.** Falta: **A13** (OpenAPI/contrato — opcional), **B12** (polish final) e **B13** (ícone/splash finais, EAS Build, contas Apple/Google, submissão às lojas).

## 4. Próximo passo (caminho recomendado)

**Concluídos:** A0/A1 (fundação+auth), A2 (users/follow), A3 (posts/feed),
A7 (picos), A11 (mídia) · B0/B1/B2 (auth app), B3 (feed/criar post), B6 (perfil),
**B8 (picos: lista/detalhe/cadastro com GPS)**. Suíte API: **34 testes**; app
`tsc` limpo + bundle Android OK.

**Falta (pares independentes):**
1. **A10 + B11 (ranking)** — simples e já pedido pelo Emanuel; reusa `main.ranking`/`gamification.py`. Bom próximo.
2. **A5 + B5 (reels)** — vídeos verticais (a aba Reels ainda é placeholder).
3. **A4 + B4 (stories)** — efêmeros 24h.
4. **A6 + A12 + B7 (mensagens + push)** — DMs e notificações push (Expo).
5. **A8 + B9 (caronas)**, **A9 + B10 (fotos à venda + pagamento)**.
6. **A7 extra:** previsão (Open-Meteo) e contribuição de pico na tela de detalhe do app.
7. Fechamento: **A13 (OpenAPI/contrato)**, **B12 (deep links)**, **B13 (EAS build + publicação nas lojas)**.

**Padrões obrigatórios** (Definition of Done, seção 4 do plano): formato de erro,
paginação e serializers da fundação; `@jwt_required()` + respeitar
`is_public`/privacidade; não quebrar o pytest do site; reusar lógica existente
(gamificação, badges, forecast Open-Meteo, Cloudinary); nada de segredo hardcoded.

### Sugestão para começar amanhã
> "Implemente o par **A10 + B11 (ranking)**: endpoint `GET /api/v1/ranking`
> (paginado, reusando `main.ranking`/`gamification.py`, com `patente`/`points`
> no serializer) e a tela de ranking no app (pódio + lista). Em seguida
> **A5 + B5 (reels)**. Rode `pytest` do backend e `npm run typecheck` do app ao
> final. Os contratos e padrões já estão em `routes/api/` e no cliente do app."
