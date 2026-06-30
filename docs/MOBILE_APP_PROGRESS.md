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
