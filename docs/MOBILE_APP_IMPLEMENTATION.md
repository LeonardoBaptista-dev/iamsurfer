# IAmSurfer — App Mobile (iOS + Android) · Plano de Implementação Sênior

> **Decisões já tomadas**
> - **Framework:** Expo / React Native (app 100% nativo).
> - **Escopo da v1:** paridade total com a web (social + picos/SurfMap/previsão + caronas + fotos à venda + gamificação).
> - **Backend atual:** Flask + Jinja, Flask-Login (sessão/cookie), Postgres, Cloudinary, ~100 rotas. **Não há API REST nem auth por token** — isso será construído.

Este documento está dividido em **prompts auto-contidos**. Cada prompt é uma tarefa fechada para um agente, com objetivo, dependências, arquivos, tarefas e critérios de aceite. Há um **grafo de dependências** mostrando o que roda em paralelo.

---

## 1. Visão geral da arquitetura

```
┌─────────────────────────────┐        HTTPS / JSON          ┌──────────────────────────────┐
│  App Expo (React Native)    │  ─────────────────────────►  │  Flask API REST  /api/v1/*    │
│  - TypeScript               │   Bearer <access_token JWT>  │  - JWT (access + refresh)     │
│  - expo-router (file-based) │  ◄─────────────────────────  │  - Serializers (to_dict)      │
│  - React Query (cache)      │        JSON paginado         │  - Rate limit + CORS          │
│  - SecureStore (tokens)     │                              │  - Mesmos models/DB de hoje   │
└─────────────────────────────┘                              └──────────────┬───────────────┘
        │  Expo Push                                                          │
        │  Cloudinary upload assinado                          Postgres (Coolify)  +  Cloudinary
        ▼
   Lojas (App Store / Google Play) via EAS Build
```

**Princípio-chave:** a API REST (`/api/v1`) é um **novo blueprint** que convive com o site Jinja atual e **reaproveita os mesmos models, DB e Cloudinary**. O site web continua funcionando sem alterações. Nada de reescrever o backend — só expor JSON + auth por token.

---

## 2. Decisões técnicas (padrões obrigatórios)

| Tema | Decisão | Observação |
|---|---|---|
| Auth da API | **flask-jwt-extended** — access token (15 min) + refresh token (30 dias, rotativo) | Mantém Flask-Login para o site web; JWT só no `/api/v1`. |
| Formato de erro | `{ "error": { "code": "string", "message": "humano", "fields": {…} } }` + status HTTP correto | Padrão único em toda a API. |
| Paginação | Cursor-based: `?cursor=<opaco>&limit=20` → `{ "items": [...], "next_cursor": "..." }` | Feeds infinitos sem `OFFSET` lento. |
| Datas | ISO-8601 UTC (`2026-06-26T14:30:00Z`) | App formata no fuso local. |
| Upload de mídia | **Upload assinado direto pro Cloudinary** (API gera assinatura, app envia o arquivo) | Não trafega binário pelo Flask. |
| Push | **Expo Push Notifications** (token salvo por device) | Sem precisar de Firebase próprio no MVP. |
| Pagamentos (fotos à venda) | **Mercado Pago (Pix + cartão)** — público BR | A decidir definitivamente no Prompt A9; Stripe é alternativa. |
| Mapas (SurfMap) | **react-native-maps** (Google no Android, Apple no iOS) | Reusa as coords já existentes nos Spots. |
| Cache/estado no app | **TanStack React Query** + SecureStore p/ tokens | Nada de Redux pra começar. |
| Versionamento da API | Prefixo `/api/v1` | Header `X-Client-Version` p/ forçar update futuramente. |

### Contrato de dados (serializers)
Cada model ganha um `to_dict(viewer=None)` (ou módulo `api/serializers.py`) com **shape estável**. Exemplo canônico de `User`:

```json
{
  "id": 12,
  "username": "leo",
  "avatar_url": "https://res.cloudinary.com/.../leo.jpg",
  "bio": "Surfista de fim de semana",
  "location": "Floripa, SC",
  "is_public": true,
  "points": 1240,
  "patente": { "name": "Local", "icon": "bi-water" },
  "counts": { "posts": 34, "followers": 210, "following": 98 },
  "viewer_state": { "is_following": false, "is_self": false }
}
```

> `viewer_state` é sempre relativo ao usuário autenticado — evita N+1 de "eu sigo essa pessoa?" no app.

---

## 3. Grafo de dependências e paralelização

```
BACKEND                                   MOBILE
A0 (fundação API+JWT) ───┐
   ├─ A1 auth            │
   ├─ A2 users/follow    │  (A1..A11 rodam em paralelo após A0)
   ├─ A3 feed/posts      │
   ├─ A4 stories         │
   ├─ A5 reels           │
   ├─ A6 msgs/notif      │
   ├─ A7 spots/forecast  │
   ├─ A8 caronas         │
   ├─ A9 fotos/pagamento │
   ├─ A10 gamificação    │
   ├─ A11 upload mídia   │
   └─ A12 push  ─────────┘
A13 OpenAPI+testes (após os demais)

B0 (scaffold) ──► B1 (api client+auth) ──┬─ B2 auth screens
                                          ├─ B3 feed       (precisa A3)
                                          ├─ B4 stories    (A4)
                                          ├─ B5 reels      (A5)
                                          ├─ B6 perfil     (A2)
                                          ├─ B7 msgs/push  (A6,A12)
                                          ├─ B8 spots/mapa (A7)
                                          ├─ B9 caronas    (A8)
                                          ├─ B10 fotos     (A9)
                                          └─ B11 ranking   (A10)
B12 (shell de navegação/tabs) integra tudo
B13 (EAS build + submit lojas) por último
```

**Caminho crítico:** `A0 → A1 → B0 → B1 → B2` (login funcionando). A partir daí, cada dupla `An/Bn` de feature é independente e paralelizável. Recomendo travar e revisar **A0** e **B1** com cuidado (contratos) antes de soltar os agentes em paralelo — eles são a fundação que todo o resto consome.

### Como distribuir entre agentes
- **1 agente "API foundation"** faz A0 sozinho (bloqueante).
- Depois, **N agentes** pegam um par `An` cada (worktrees isolados recomendados — `isolation: worktree` — pois mexem em arquivos diferentes).
- **1 agente "mobile foundation"** faz B0+B1 (bloqueante para o app).
- Depois **N agentes** pegam `Bn` cada.
- A13, B12, B13 são de **integração** — um agente sênior fecha.

---

## 4. Convenções para TODOS os prompts (Definition of Done global)

Cada PR de agente só está "pronto" se:
1. ✅ Segue o **formato de erro**, **paginação** e **serializers** da seção 2.
2. ✅ Endpoints protegidos exigem `@jwt_required()`; respeitam `is_public`/bloqueios/privacidade já existentes na web.
3. ✅ Não quebra nenhuma rota do site Jinja (rodar a suíte `pytest` atual).
4. ✅ Tem testes (pytest no backend; ao menos smoke no app).
5. ✅ Nenhum segredo hardcoded — tudo via env (`.env` / EAS secrets).
6. ✅ Reusa lógica existente (gamificação, badges, forecast, Cloudinary) em vez de duplicar.

---

# PARTE A — Backend: API REST + JWT

## Prompt A0 — Fundação da API (`/api/v1`) + JWT
**Depende de:** nada · **Bloqueia:** todos os outros prompts A e B.

**Objetivo:** criar a base da API que todos os endpoints vão herdar.

**Tarefas**
- Adicionar `flask-jwt-extended`, `flask-cors`, `flask-limiter` ao `requirements.txt`.
- Criar pacote `routes/api/__init__.py` registrando blueprint `api` com prefixo `/api/v1`.
- Configurar JWT: access (15 min), refresh (30 dias, **rotativo** com blocklist em tabela `token_blocklist`), chaves via env.
- CORS liberado para o app (origins via env), rate limit padrão (ex.: 120/min por IP, 5/min em login).
- Handlers globais: erro padrão `{ "error": {...} }`, 401/403/404/422/429/500.
- Utilitários: `paginate(query, cursor, limit)` cursor-based; decorator `@api_route` opcional; helper `current_api_user()`.
- Criar `routes/api/serializers.py` com o `to_dict` canônico de `User` (seção 2) e o esqueleto p/ os demais.
- Healthcheck `GET /api/v1/ping` → `{ "ok": true, "version": "1" }`.

**Critérios de aceite:** `GET /api/v1/ping` responde; um teste prova que rota protegida sem token dá 401 no formato padrão; site web intacto.

**PROMPT PARA O AGENTE:**
> Você está no projeto Flask IAmSurfer (Flask 2.0.1, Flask-Login, Postgres, Cloudinary). Crie a fundação de uma API REST versionada em `/api/v1` usando flask-jwt-extended, sem tocar nas rotas Jinja existentes. Implemente: blueprint `routes/api`, auth JWT (access 15min + refresh 30d rotativo com blocklist em tabela), CORS e rate limit por env, formato de erro único `{"error":{"code","message","fields"}}`, paginação cursor-based, `routes/api/serializers.py` com `User.to_dict(viewer)` conforme o contrato do doc `docs/MOBILE_APP_IMPLEMENTATION.md` seção 2, e `GET /api/v1/ping`. Adicione migration p/ a blocklist. Escreva testes pytest cobrindo ping e 401. Não quebre a suíte existente.

---

## Prompt A1 — Auth (registro, login, refresh, eu)
**Depende de:** A0.

**Endpoints**
- `POST /api/v1/auth/register` → cria user (reusa validações do `routes/auth.py`), retorna tokens + user.
- `POST /api/v1/auth/login` → aceita email **ou** username (case-insensitive, igual à web), retorna access+refresh+user.
- `POST /api/v1/auth/refresh` → novo access (rotaciona refresh, revoga o antigo).
- `POST /api/v1/auth/logout` → revoga o refresh atual.
- `GET  /api/v1/auth/me` → user autenticado (serializer completo).
- `POST /api/v1/auth/push-token` → registra/atualiza Expo push token do device (tabela `device_token`: user_id, token, platform, updated_at).

**Aceite:** fluxo register→login→refresh→me→logout coberto por teste; senha nunca volta no JSON.

**PROMPT:** *Implemente os endpoints de auth da API (`/api/v1/auth/*`) reusando a lógica de `routes/auth.py` e o `User` serializer. Login aceita email ou username case-insensitive (igual à web). Inclua registro de Expo push token por device (nova tabela + migration). Testes pytest do fluxo completo.*

---

## Prompt A2 — Usuários, perfis e follow
**Depende de:** A0 (idealmente A1 p/ testar logado).

**Endpoints**
- `GET /api/v1/users/:username` → perfil + `viewer_state` + `counts`.
- `GET /api/v1/users/:username/posts` (paginado), `.../followers`, `.../following`.
- `POST /api/v1/users/:username/follow` / `DELETE` (unfollow). Respeita perfis privados (pedido de follow se aplicável à web).
- `GET /api/v1/me` editar: `PATCH /api/v1/me` (bio, location, is_public), `PATCH /api/v1/me/avatar` (via mídia, ver A11).
- `GET /api/v1/search/users?q=`.

**Aceite:** privacidade respeitada; follow idempotente; testes.

**PROMPT:** *Exponha perfis, listas de seguidores/seguindo (paginadas), follow/unfollow idempotente respeitando `is_public`, edição do próprio perfil e busca de usuários. Reuse a lógica de follow já existente em `routes/main.py`. Serializers no contrato do doc.*

---

## Prompt A3 — Feed, posts, comentários, likes
**Depende de:** A0, A11 (upload) p/ criar post com mídia.

**Endpoints**
- `GET /api/v1/feed` (cursor) — mesma regra do feed web (de quem o user segue + próprios).
- `GET /api/v1/posts/:id` · `POST /api/v1/posts` (texto + mídia[] + spot opcional) · `DELETE /api/v1/posts/:id`.
- `POST /api/v1/posts/:id/like` / `DELETE` · `GET /api/v1/posts/:id/comments` (cursor) · `POST .../comments` · `DELETE /api/v1/comments/:id`.
- `GET /api/v1/explore` (descoberta, igual `main.explore`).

**Aceite:** like/comentário disparam Notification (reusa lógica web); contadores corretos; paginação estável.

**PROMPT:** *Implemente feed (cursor), CRUD de posts com mídia e spot opcional, likes e comentários, e explore. Reuse a montagem de feed e a criação de Notification do `routes/posts.py`/`main.py`. `Post.to_dict(viewer)` deve trazer `media[]`, `author`, `counts`, `viewer_state.liked`.*

---

## Prompt A4 — Stories
**Depende de:** A0, A11.

**Endpoints:** `GET /api/v1/stories` (story bar agrupada por usuário, como em `main/story_bar.html`), `POST /api/v1/stories` (imagem/vídeo), `POST /api/v1/stories/:id/seen`, `DELETE /api/v1/stories/:id`. Expira em 24h (regra atual).

**PROMPT:** *Exponha a story bar agrupada (mesmo shape do `story_bar.html` que o web usa), criação, marcar-visto e deleção, reusando `routes/stories.py`. Inclua `type` (image/video), `url`, `when`, `can_delete`, `has_unseen`.*

---

## Prompt A5 — Reels
**Depende de:** A0, A11. **Endpoints:** `GET /api/v1/reels` (cursor, vídeos verticais), `POST /api/v1/reels`, like/comment reusando A3. **PROMPT:** *Endpoint de reels paginado consumindo a mesma fonte de `main.reels`, com `video_url`, `author`, `counts`, `viewer_state`.*

---

## Prompt A6 — Mensagens e notificações
**Depende de:** A0, A12 (push). **Endpoints:** inbox (`GET /api/v1/conversations`), conversa (`GET /api/v1/conversations/:username`, cursor), `POST /api/v1/conversations/:username/messages`, `GET /api/v1/notifications` (cursor), `POST /api/v1/notifications/read`, `GET /api/v1/notifications/count` (já existe equivalente). Enviar mensagem/gerar notificação dispara push (A12). **PROMPT:** *Exponha mensagens e notificações reusando `routes/messages.py`; toda nova mensagem/notificação enfileira um Expo push pro destinatário.*

---

## Prompt A7 — Picos (SurfMap), previsão e fotos do pico
**Depende de:** A0. **Endpoints:** `GET /api/v1/spots` (lista + filtro/bbox p/ mapa), `GET /api/v1/spots/:id`, `GET /api/v1/spots/:id/forecast` (reusa `surf_forecast.py`/Open-Meteo), `GET /api/v1/forecast?country=`, contribuições de pico (`POST`), seguir pico. **PROMPT:** *Exponha picos com coordenadas p/ o mapa (suporte a bounding box), detalhe, previsão via `surf_forecast.py` (Open-Meteo, conforme memória do projeto — não Windguru), e seguir/contribuir pico reusando `routes/spots.py`.*

---

## Prompt A8 — Caronas (trips)
**Depende de:** A0. **Endpoints:** `GET /api/v1/trips` (cursor/filtros), `GET/POST /api/v1/trips`, `POST /api/v1/trips/:id/join` / `leave`, `GET /api/v1/me/trips`. **PROMPT:** *Exponha listagem/criação de caronas, participação (join/leave) e "minhas caronas" reusando `routes/trips.py`.*

---

## Prompt A9 — Fotos à venda + pagamentos
**Depende de:** A0, A11. **Decisão a fechar:** provedor de pagamento — **recomendado Mercado Pago (Pix + cartão)** p/ público BR; alternativa Stripe.

**Endpoints:** sessões de foto (`GET /api/v1/photo-sessions`, `:id`), `POST /api/v1/photos/:id/purchase` → cria preferência de pagamento e devolve URL/QR Pix; `POST /api/v1/webhooks/payments` (confirma compra, libera download); `GET /api/v1/me/purchases`. Cupons reusando lógica atual.

**Aceite:** webhook idempotente; foto só liberada após pagamento confirmado; valores validados no servidor (nunca confiar no client).

**PROMPT:** *Implemente compra de fotos via Mercado Pago (Pix + cartão): criação de preferência, webhook de confirmação idempotente, liberação do download só após pagamento, "minhas compras" e cupons. Reuse os models de PhotoSession/SessionPhoto/PhotoPurchase. Documente as envs do Mercado Pago.*

---

## Prompt A10 — Gamificação, badges e ranking
**Depende de:** A0. **Endpoints:** `GET /api/v1/ranking` (paginado, reusa `main.ranking`), `GET /api/v1/users/:username/badges`, incluir `patente`/`points` no serializer de user (já no contrato). **PROMPT:** *Exponha ranking e badges reusando `gamification.py`/`badges.py`; garanta que `patente` e `points` venham no `User.to_dict`.*

---

## Prompt A11 — Upload de mídia (Cloudinary assinado)
**Depende de:** A0. **Bloqueia:** A3, A4, A5, A9 (qualquer criação com mídia).

**Endpoints:** `POST /api/v1/media/sign` → retorna assinatura + params p/ o app subir **direto** no Cloudinary; `POST /api/v1/media/confirm` (opcional) p/ registrar `public_id`/derivadas. Reusa config Cloudinary atual. Suporta imagem e vídeo; valida tamanho/tipo.

**PROMPT:** *Implemente upload assinado pro Cloudinary: endpoint que gera assinatura/timestamp/folder pro app enviar o binário direto, e confirmação opcional. Reuse a config Cloudinary do projeto. O binário NÃO passa pelo Flask.*

---

## Prompt A12 — Backend de push (Expo)
**Depende de:** A0, A1 (device_token). **Tarefas:** serviço `push.py` que envia via Expo Push API (lote, trata `DeviceNotRegistered` removendo token morto), pontos de disparo: nova mensagem, novo follower, like/comentário, compra confirmada. Idempotência e retry. **PROMPT:** *Crie um serviço de envio de Expo Push (lote + limpeza de tokens inválidos) e ligue-o aos eventos: mensagem, follower, like, comentário, compra. Reuse a criação de Notification existente como gatilho.*

---

## Prompt A13 — OpenAPI + testes de contrato
**Depende de:** A1–A12. **Tarefas:** gerar/escrever spec OpenAPI 3.1 (`docs/api/openapi.yaml`) cobrindo todos os endpoints, servir `GET /api/v1/openapi.json`, suíte de testes de contrato (status, shape, auth, paginação). Exportar uma **collection** (Insomnia/Postman). **PROMPT:** *Documente toda a API em OpenAPI 3.1, sirva o JSON e escreva testes de contrato garantindo shapes/erros/paginação. Gere uma collection importável para o time mobile.*

---

# PARTE B — App Mobile (Expo / React Native)

> Pasta sugerida: **repositório separado** `iamsurfer-app/` (monorepo opcional). TypeScript estrito. `expo-router`.

## Prompt B0 — Scaffold do app + design system
**Depende de:** nada (pode começar junto com A0). **Bloqueia:** todo o resto do app.

**Tarefas**
- `npx create-expo-app` (TypeScript, expo-router), configurar EAS (`eas.json`).
- Design system fiel à marca: indigo `#3730a3` (`--brand`), neutros, fonte Inter, tema claro. Componentes base: `Button`, `Avatar`, `Card`, `Input`, `Tabbar`, ícones (estilo Instagram do navbar web — ícone + rótulo).
- Estrutura de pastas: `app/` (rotas), `src/api`, `src/components`, `src/hooks`, `src/theme`, `src/lib`.
- Env por ambiente (`API_URL` dev/prod), React Query provider, SafeArea, splash/ícone placeholder.

**Aceite:** app roda no Expo Go, mostra tela placeholder com o tema/cores da marca.

**PROMPT:** *Crie o app Expo (TypeScript + expo-router) `iamsurfer-app`. Monte um design system fiel à marca IAmSurfer (indigo #3730a3, neutros, Inter, navbar inferior estilo Instagram com ícone+rótulo igual ao web). Configure EAS, React Query, SafeArea e envs de API. Entregue rodando no Expo Go com tema aplicado.*

---

## Prompt B1 — Cliente HTTP + fluxo de auth (tokens)
**Depende de:** B0, A0/A1. **Bloqueia:** todas as features.

**Tarefas**
- Cliente `src/api/client.ts` (fetch/axios) com base URL, injeção de `Authorization: Bearer`, **interceptor de refresh** (em 401 tenta refresh, re-tenta a request; se falhar, desloga).
- Tokens em **expo-secure-store**. `AuthContext`/store com `signIn/signOut/restore`.
- Mapear o formato de erro padrão da API em mensagens amigáveis (toasts).
- Registro de Expo push token no login (chama `POST /auth/push-token`).

**Aceite:** login persiste sessão entre reaberturas; expiração de access é transparente via refresh.

**PROMPT:** *Implemente o cliente HTTP com Bearer + interceptor de refresh automático (401 → refresh → retry → senão signOut), armazenamento de tokens no SecureStore, AuthContext e tratamento do formato de erro padrão da API. Registre o Expo push token após login.*

---

## Prompt B2 — Telas de autenticação
**Depende de:** B1, A1. **Telas:** Splash, Login (email/username + senha), Cadastro, recuperação (se a web tiver). Validação inline, estados de loading/erro. **PROMPT:** *Construa as telas de login/cadastro usando o AuthContext e o design system, com validação e feedback de erro vindos da API.*

---

## Prompt B3 — Feed + post + criar post
**Depende de:** B1, A3, A11. **Telas:** Feed (lista infinita via React Query `useInfiniteQuery`), card de post (mídia, like otimista, comentários), detalhe do post, criar post (picker de imagem/vídeo → upload assinado A11 → cria post). **PROMPT:** *Implemente o feed infinito, card de post com like otimista e comentários, detalhe e criação de post com upload de mídia assinado. Cursor-based, com pull-to-refresh.*

---

## Prompt B4 — Stories (viewer + criação)
**Depende de:** B1, A4. **Telas:** barra de stories (topo do feed), **viewer full-screen** com barras de progresso, toque p/ avançar/voltar, vídeo/imagem, marcar visto, criar story. (Portar a lógica do viewer de `main/story_bar.html`.) **PROMPT:** *Construa a story bar e o viewer full-screen (progresso, gestos, auto-advance, mute em vídeo) consumindo a API de stories, espelhando o comportamento do viewer web.*

---

## Prompt B5 — Reels
**Depende de:** B1, A5. **Tela:** feed vertical de vídeos (swipe full-screen, autoplay no foco, like/comentário, `expo-av`/`expo-video`). **PROMPT:** *Implemente a tela de Reels (vídeo vertical full-screen com snap, autoplay do item visível, like/comentário) consumindo a API de reels.*

---

## Prompt B6 — Perfil + edição + follow
**Depende de:** B1, A2. **Telas:** perfil próprio e de terceiros (header com counts, grid de posts, patente/badges), seguir/deixar de seguir, listas de seguidores/seguindo, editar perfil (bio/location/privacidade/avatar). **PROMPT:** *Construa as telas de perfil (próprio e de terceiros), grid de posts, follow/unfollow otimista, listas de seguidores/seguindo e edição de perfil com troca de avatar (upload assinado).*

---

## Prompt B7 — Mensagens + notificações + push
**Depende de:** B1, A6, A12. **Telas:** inbox, conversa (chat), tela de notificações; configurar **expo-notifications** (permissão, recebimento em foreground/background, deep link ao tocar). Badge no ícone da tab. **PROMPT:** *Implemente inbox, chat e notificações, e configure expo-notifications (permissão, handlers, deep link ao tocar). Mostre badge de não-lidos na tabbar.*

---

## Prompt B8 — Picos / SurfMap + previsão
**Depende de:** B1, A7. **Telas:** mapa (`react-native-maps`) com marcadores dos picos (carrega por bounding box), detalhe do pico (fotos, seguir), tela de previsão (Open-Meteo) com gráfico simples. **PROMPT:** *Construa o SurfMap com react-native-maps (marcadores por bbox), detalhe do pico e a tela de previsão consumindo a API. Use a mesma identidade visual sóbria do app.*

---

## Prompt B9 — Caronas
**Depende de:** B1, A8. **Telas:** lista/busca de caronas, detalhe, criar carona, participar/sair, "minhas caronas". **PROMPT:** *Implemente listagem, detalhe, criação e participação de caronas consumindo a API.*

---

## Prompt B10 — Fotos à venda + checkout
**Depende de:** B1, A9. **Telas:** sessões/galeria de fotos do pico, detalhe da foto (com marca d'água até comprar), checkout (Pix QR / cartão via Mercado Pago), "minhas compras" com download. **PROMPT:** *Construa a vitrine de fotos à venda, o checkout via Mercado Pago (Pix QR + cartão) e "minhas compras" com download liberado pós-pagamento. Trate o retorno do webhook via polling/refresh do status.*

---

## Prompt B11 — Ranking + gamificação
**Depende de:** B1, A10. **Telas:** ranking, exibição de patente/badges no perfil. **PROMPT:** *Implemente a tela de ranking e a exibição de patente/badges, consumindo a API de gamificação.*

---

## Prompt B12 — Shell de navegação + deep links
**Depende de:** B2–B11. **Tarefas:** bottom tabs definitivos (Início · Explorar · Criar · Reels · Perfil — espelhando o navbar web), top bar com notificação/mensagens, deep linking (`iamsurfer://` + universal links), tratamento de sessão expirada global, estados vazios/erro/offline. **PROMPT:** *Monte o shell de navegação final (tabs + top bar espelhando o web), deep links e universal links, e o tratamento global de sessão/erro/offline.*

---

## Prompt B13 — Build, ícones e publicação nas lojas
**Depende de:** tudo. **Tarefas:** ícone/splash finais, `app.json` (bundle id, permissões iOS/Android com textos de uso de câmera/notificação), **EAS Build** (iOS + Android), contas Apple Developer ($99/ano) e Google Play ($25 único), screenshots, política de privacidade (já existe `/privacidade`), submissão (`eas submit`), build de teste (TestFlight / Internal testing). **PROMPT:** *Configure ícones/splash, permissões e metadados das lojas, rode EAS Build p/ iOS e Android, prepare screenshots e textos, e submeta para TestFlight e Google Play Internal Testing. Documente o processo no README do app.*

---

## 5. Riscos & atenção
- **App review da Apple:** garantir login funcional p/ revisor (conta demo já existe via `seed_demo.py`), HTTPS, e política de privacidade linkada.
- **Pagamentos:** valor/validação **sempre** no servidor; webhook idempotente; nunca liberar foto pelo client.
- **Privacidade:** API deve respeitar `is_public`/bloqueios exatamente como a web — testar com conta privada.
- **Mídia:** vídeos pesados → usar upload assinado direto + limites de tamanho/duração.
- **Versionamento:** já nascer com `/api/v1` e header de versão do client p/ poder forçar update.
- **Custos recorrentes:** Apple Developer (US$99/ano), Google Play (US$25 único), possível aumento de uso do Cloudinary/Mercado Pago.

## 6. Sequência recomendada de execução
1. **A0** (sozinho, revisar contratos) → **A1** + **B0** em paralelo.
2. **B1** (auth no app) assim que A1 estiver de pé → valida o caminho crítico (login real).
3. Soltar agentes em paralelo: cada dupla `An/Bn` (A2/B6, A3/B3, A4/B4, …) em worktrees isolados.
4. **A11** cedo (desbloqueia mídia de A3/A4/A5/A9).
5. **A12 + B7** (push) depois de mensagens.
6. **A13** (contrato) trava a API; **B12** integra a navegação; **B13** publica.
```
```

---

*Documento vivo — atualize os critérios de aceite conforme os contratos forem fechados em A0/A13.*
