# AGORA — Plateforme de Connaissance Collaborative
> *La place publique de la connaissance*

---

## ⚠️ Instructions pour Claude Code

**Claude ne figure pas parmi les contributeurs de ce projet.** Son rôle est exclusivement d'assister le développement sous la direction et supervision du développeur principal.

**Chaque ligne de code produite est relue et validée par des experts.** En conséquence :
- Zéro approximation tolérée
- Zéro code non testé
- Zéro dépendance inutile
- Toujours privilegier la lisibilité, la robustesse et la maintenabilité
- Documenter chaque fonction, endpoint, et module
- Respecter scrupuleusement les conventions définies dans ce document
- En cas de doute sur une implémentation, signaler explicitement plutôt qu'improviser
- Ne jamais générer de code "placeholder" sans le signaler clairement

---

## 📋 Vue d'ensemble du projet

**Agora** est une plateforme open source de connaissance collaborative destinée aux chercheurs, étudiants et curieux. Elle permet de :

- Uploader et lire des documents multi-formats (PDF, liens web, vidéos, images)
- Organiser ses ressources en boards publics thématiques
- Poser des questions en langage naturel sur l'ensemble de ses documents (RAG)
- Contribuer aux boards d'autres utilisateurs (avec validation par l'auteur)
- Découvrir automatiquement des livres, articles scientifiques et vidéos pertinents via des APIs publiques
- Construire un graphe de connaissance collectif et interconnecté

---

## 🏗️ Architecture Microservices

```
agora/
├── services/
│   ├── gateway/           # Point d'entrée unique, routing, auth middleware
│   ├── auth/              # Authentification username/password + JWT
│   ├── boards/            # CRUD boards, collections, connexions
│   ├── content/           # Upload et stockage des fichiers
│   ├── ingestion/         # Pipeline de parsing multi-format
│   ├── search/            # RAG, embeddings, ChromaDB, Q&A
│   └── discovery/         # Suggestions via APIs externes
├── frontend/              # React + TailwindCSS
├── shared/                # Schémas Pydantic partagés, utils communs
├── infra/                 # Configs Docker, Nginx, scripts
├── docs/                  # Documentation technique
├── tests/                 # Tests d'intégration inter-services
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
└── README.md
```

---

## 🔧 Stack Technique

### Backend
| Composant | Technologie | Version |
|-----------|-------------|---------|
| Framework API | FastAPI | ≥ 0.111 |
| Validation | Pydantic v2 | ≥ 2.7 |
| ORM | SQLAlchemy | ≥ 2.0 |
| Migrations | Alembic | ≥ 1.13 |
| Auth | python-jose + passlib[bcrypt] | latest |
| Queue async | Redis + RQ | latest |
| HTTP client | httpx | ≥ 0.27 |

### Bases de données
| Usage | Technologie |
|-------|-------------|
| Données relationnelles | PostgreSQL 16 |
| Vectors / embeddings | ChromaDB |
| Cache + queues | Redis 7 |
| Stockage fichiers | MinIO (compatible S3) |

### IA / ML
> ⚠️ **À définir** — Le choix des modèles (LLM, embeddings, transcription, vision) et de la stratégie d'inférence (local, API, streaming) sera déterminé lors de la phase ML du projet.

### Frontend
| Composant | Technologie |
|-----------|-------------|
| Framework | React 18 |
| Styling | TailwindCSS v3 |
| PDF Viewer | react-pdf (PDF.js) |
| State management | Zustand |
| HTTP client | axios |
| Router | React Router v6 |

### Infrastructure
| Composant | Technologie |
|-----------|-------------|
| Containerisation | Docker + Docker Compose |
| Reverse proxy | Nginx |
| CI/CD | GitHub Actions |

---

## 🌐 Services — Détail

### 1. `gateway` — Port 8000
Point d'entrée unique de l'application.

**Responsabilités :**
- Reverse proxy vers les microservices internes
- Validation du JWT sur toutes les routes protégées
- Rate limiting global
- Logging centralisé des requêtes

**Endpoints exposés :**
```
/api/auth/*       → auth service
/api/boards/*     → boards service
/api/content/*    → content service
/api/search/*     → search service
/api/discovery/*  → discovery service
```

---

### 2. `auth` — Port 8001
Authentification et gestion des utilisateurs.

**Responsabilités :**
- Inscription (username + password)
- Connexion → retourne JWT
- Gestion du profil utilisateur
- Système de réputation (score calculé)

**Modèle de données :**
```sql
users
  id            UUID PRIMARY KEY
  username      VARCHAR(50) UNIQUE NOT NULL
  password_hash VARCHAR(255) NOT NULL
  bio           TEXT
  reputation    INTEGER DEFAULT 0
  created_at    TIMESTAMP DEFAULT NOW()
  updated_at    TIMESTAMP
```

**Endpoints :**
```
POST /register          → créer un compte
POST /login             → retourne access_token (JWT)
GET  /me                → profil de l'utilisateur connecté
GET  /users/:username   → profil public
PUT  /me                → mise à jour du profil
```

**Sécurité :**
- Passwords hashés avec bcrypt (cost factor 12)
- JWT avec expiration 7 jours
- Pas de refresh token en V1 (simplicité)

---

### 3. `boards` — Port 8002
Gestion des boards, collections et contributions.

**Responsabilités :**
- CRUD boards
- Gestion des items dans un board
- Système de contribution + validation
- Connexions entre items

**Modèle de données :**
```sql
boards
  id           UUID PRIMARY KEY
  owner_id     UUID REFERENCES users(id)
  title        VARCHAR(255) NOT NULL
  description  TEXT
  tags         TEXT[]
  is_public    BOOLEAN DEFAULT TRUE
  created_at   TIMESTAMP DEFAULT NOW()
  updated_at   TIMESTAMP

board_items
  id           UUID PRIMARY KEY
  board_id     UUID REFERENCES boards(id)
  content_id   UUID REFERENCES contents(id)
  added_by     UUID REFERENCES users(id)
  status       ENUM('pending', 'validated', 'rejected') DEFAULT 'validated'
  created_at   TIMESTAMP DEFAULT NOW()

contributions
  id              UUID PRIMARY KEY
  board_item_id   UUID REFERENCES board_items(id)
  contributor_id  UUID REFERENCES users(id)
  type            ENUM('annotation', 'link', 'comment')
  body            TEXT
  status          ENUM('pending', 'validated', 'rejected') DEFAULT 'pending'
  created_at      TIMESTAMP DEFAULT NOW()

item_connections
  id         UUID PRIMARY KEY
  item_a_id  UUID REFERENCES board_items(id)
  item_b_id  UUID REFERENCES board_items(id)
  label      VARCHAR(255)
  created_by UUID REFERENCES users(id)
  created_at TIMESTAMP DEFAULT NOW()
```

**Endpoints :**
```
GET    /boards                    → liste des boards publics
POST   /boards                    → créer un board
GET    /boards/:id                → détail d'un board
PUT    /boards/:id                → modifier un board
DELETE /boards/:id                → supprimer un board
POST   /boards/:id/items          → ajouter un item au board
DELETE /boards/:id/items/:item_id → retirer un item
POST   /boards/:id/items/:item_id/contribute  → soumettre une contribution
GET    /boards/:id/contributions  → lister les contributions en attente
PUT    /contributions/:id/validate → valider une contribution
PUT    /contributions/:id/reject   → rejeter une contribution
POST   /boards/:id/items/connect  → créer une connexion entre deux items
```

---

### 4. `content` — Port 8003
Upload et stockage des contenus.

**Responsabilités :**
- Upload de fichiers vers MinIO
- Enregistrement des métadonnées
- Gestion des types de contenu (PDF, URL, image, vidéo)
- Déclenchement de l'ingestion asynchrone

**Modèle de données :**
```sql
contents
  id           UUID PRIMARY KEY
  owner_id     UUID REFERENCES users(id)
  type         ENUM('pdf', 'url', 'image', 'video', 'note')
  title        VARCHAR(500)
  source_url   TEXT
  storage_key  VARCHAR(500)       -- clé MinIO si fichier uploadé
  status       ENUM('pending', 'processing', 'ready', 'error') DEFAULT 'pending'
  metadata     JSONB              -- taille, durée, nb pages, etc.
  created_at   TIMESTAMP DEFAULT NOW()
  updated_at   TIMESTAMP
```

**Endpoints :**
```
POST /upload          → upload fichier (PDF, image)
POST /link            → ajouter un lien (URL, TikTok, YouTube, Pinterest)
GET  /contents/:id    → métadonnées d'un contenu
GET  /contents/:id/file → stream du fichier (PDF)
DELETE /contents/:id  → supprimer un contenu
```

**Gestion des types :**
- `pdf` → upload direct → MinIO → ingestion
- `url` → scraping Playwright → ingestion
- `video` (YouTube/TikTok) → extraction URL → Whisper → ingestion
- `image` → upload → MinIO → LLaVA description → ingestion
- `note` → texte direct → ingestion immédiate

---

### 5. `ingestion` — Port 8004
Pipeline de traitement asynchrone des contenus.

**Responsabilités :**
- Écouter la queue Redis pour les jobs d'ingestion
- Parser chaque type de contenu
- Chunker le texte extrait
- Générer les embeddings
- Stocker dans ChromaDB
- Mettre à jour le statut dans PostgreSQL

**Pipeline par type :**

```
PDF
  PyMuPDF → extraction texte + numéros de page
  → chunking → embeddings → ChromaDB

URL
  Playwright → scraping HTML → BeautifulSoup → nettoyage
  → chunking → embeddings → ChromaDB

VIDEO (YouTube / TikTok)
  yt-dlp → téléchargement audio
  → transcription (modèle à définir)
  → chunking → embeddings → ChromaDB

IMAGE
  MinIO → téléchargement
  → description textuelle (modèle vision à définir)
  → embeddings → ChromaDB

NOTE
  Texte brut → chunking → embeddings → ChromaDB
```

> ⚠️ **Modèles d'embeddings, de transcription et de vision à définir lors de la phase ML.**

**Stratégie de chunking :**
- Taille et overlap : à définir lors de la phase ML
- Préservation des limites de paragraphes
- Métadonnées conservées : `content_id`, `page_number`, `chunk_index`, `owner_id`, `board_ids`

---

### 6. `search` — Port 8005
Moteur RAG et recherche sémantique.

**Responsabilités :**
- Recevoir une question en langage naturel
- Retrieval des chunks pertinents (ChromaDB)
- Génération de la réponse via LLM
- Retourner les références précises (document, page, auteur)
- Stratégie hybride CAG/RAG selon taille du document

**Stratégie RAG :**

> ⚠️ **La stratégie complète (CAG, RAG hybride, modèle LLM, embeddings, paramètres de retrieval) sera définie lors de la phase ML du projet.**

Ce qui est acté :
- Retrieval depuis ChromaDB
- Réponse avec références précises (document, page, auteur)
- Format de réponse standardisé (voir ci-dessous)

**Endpoints :**
```
POST /query              → Q&A sur un ou plusieurs contenus
POST /query/board/:id    → Q&A sur tout un board
GET  /similar/:content_id → contenus similaires
```

**Format de réponse :**
```json
{
  "answer": "...",
  "sources": [
    {
      "content_id": "uuid",
      "title": "nom du document",
      "page": 4,
      "excerpt": "passage pertinent...",
      "score": 0.92
    }
  ]
}
```

---

### 7. `discovery` — Port 8006
Suggestions de ressources via APIs publiques.

**Responsabilités :**
- Extraire les mots-clés d'un board (titre + tags)
- Appeler les APIs externes en parallèle
- Agréger, dédupliquer, trier les résultats
- Retourner les suggestions enrichies

**APIs utilisées :**
| Source | API | Tri |
|--------|-----|-----|
| Livres | Open Library API | Popularité (nombre d'éditions) |
| Articles | Semantic Scholar API | Nombre de citations |
| Articles | arXiv API | Date de publication |
| Vidéos | YouTube Data API v3 | Vues + durée (favoriser > 20min) |
| Encyclopédie | Wikipedia API | Pertinence |

**Endpoints :**
```
GET /suggest/:board_id          → suggestions pour un board
GET /suggest?q=query&type=books → suggestions ad hoc
```

**Format de réponse :**
```json
{
  "books": [...],
  "articles": [...],
  "videos": [...],
  "wikipedia": [...]
}
```

---

## 🔐 Authentification & Sécurité

- **Méthode** : username + password uniquement (pas d'OAuth en V1)
- **Hashing** : bcrypt avec cost factor 12
- **Token** : JWT signé HS256, expiration 7 jours
- **Transport** : Header `Authorization: Bearer <token>`
- **Validation** : middleware dans le gateway sur toutes les routes `/api/*` sauf `/api/auth/login` et `/api/auth/register`
- **Permissions** :
  - Lecture des boards publics : non authentifié autorisé
  - Création/modification : authentifié requis
  - Validation contributions : owner du board uniquement

---

## 📡 Communication Inter-Services

### Synchrone (HTTP interne)
Pour les requêtes qui nécessitent une réponse immédiate :
- Gateway → tous les services
- Search → Content (récupérer métadonnées)
- Boards → Content (vérifier existence d'un contenu)

### Asynchrone (Redis Queue)
Pour les tâches longues :
- Content → Redis Queue → Ingestion
- Queue nommée : `agora:ingestion`
- Format du job :
```json
{
  "content_id": "uuid",
  "type": "pdf",
  "storage_key": "uploads/uuid.pdf",
  "owner_id": "uuid"
}
```

---

## 🐳 Infrastructure Docker

### Services Docker Compose
```yaml
services:
  postgres:    image: postgres:16-alpine,    port: 5432
  redis:       image: redis:7-alpine,        port: 6379
  chromadb:    image: chromadb/chroma,       port: 8888
  minio:       image: minio/minio,           ports: 9000/9001
  gateway:     build: ./services/gateway,    port: 8000
  auth:        build: ./services/auth,       port: 8001
  boards:      build: ./services/boards,     port: 8002
  content:     build: ./services/content,    port: 8003
  ingestion:   build: ./services/ingestion,  port: 8004
  search:      build: ./services/search,     port: 8005
  discovery:   build: ./services/discovery,  port: 8006
  frontend:    build: ./frontend,            port: 3000
```

> ⚠️ **Le service LLM (Ollama, API externe, ou autre) sera ajouté lors de la phase ML.**

### Variables d'environnement (.env)
```env
# PostgreSQL
POSTGRES_USER=agora
POSTGRES_PASSWORD=<secret>
POSTGRES_DB=agora

# Redis
REDIS_URL=redis://redis:6379

# ChromaDB
CHROMA_HOST=chromadb
CHROMA_PORT=8888

# MinIO
MINIO_ROOT_USER=agora
MINIO_ROOT_PASSWORD=<secret>
MINIO_BUCKET=agora-content

# JWT
JWT_SECRET=<secret-256-bits>
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# YouTube API
YOUTUBE_API_KEY=<secret>

# LLM & Embeddings — ⚠️ À définir lors de la phase ML
```

---

## 🗺️ Roadmap de Développement

### V1 — MVP (Phase actuelle)
- [ ] Structure du projet + Docker Compose
- [ ] Service `auth` : register, login, JWT
- [ ] Service `content` : upload PDF, stockage MinIO
- [ ] Service `ingestion` : parsing PDF, embeddings, ChromaDB
- [ ] Service `search` : RAG basique sur un document
- [ ] Service `gateway` : routing + auth middleware
- [ ] Frontend : auth, upload PDF, PDF viewer, chat Q&A

### V2 — Collaboration
- [ ] Service `boards` : CRUD complet
- [ ] Système de contributions + validation
- [ ] Profils publics + réputation
- [ ] Annotations et surlignage dans le PDF viewer
- [ ] RAG multi-documents (scope board)

### V3 — Multi-format
- [ ] Ingestion URL (scraping web)
- [ ] Ingestion vidéo (transcription)
- [ ] Ingestion image (vision)
- [ ] Ingestion notes texte

### V4 — Découverte
- [ ] Service `discovery` : Open Library, arXiv, Semantic Scholar, YouTube
- [ ] Suggestions automatiques par board
- [ ] Import en un clic depuis les suggestions

### V5 — ML (à définir)
- [ ] Choix des modèles LLM, embeddings, transcription, vision
- [ ] Stratégie d'inférence (local vs API, streaming)
- [ ] Optimisation du pipeline RAG
- [ ] Fine-tuning éventuel

---

## 📏 Conventions de Code

### Python (tous les services backend)
- Style : **PEP 8** strict
- Formatter : **black** (line-length 88)
- Linter : **ruff**
- Type hints : **obligatoires** sur toutes les fonctions
- Docstrings : **Google style** sur toutes les fonctions publiques
- Tests : **pytest** avec coverage minimum 80%

### Structure d'un service FastAPI
```
services/auth/
├── app/
│   ├── __init__.py
│   ├── main.py          # app FastAPI, lifespan, middleware
│   ├── config.py        # settings Pydantic BaseSettings
│   ├── dependencies.py  # dépendances FastAPI (get_db, get_current_user)
│   ├── models/          # modèles SQLAlchemy
│   ├── schemas/         # schémas Pydantic (request/response)
│   ├── routers/         # endpoints FastAPI
│   ├── services/        # logique métier
│   └── utils/           # utilitaires
├── tests/
│   ├── conftest.py
│   └── test_*.py
├── Dockerfile
├── requirements.txt
└── alembic/             # migrations (si service avec DB)
```

### TypeScript/React (frontend)
- Style : **ESLint + Prettier**
- Composants : **fonctionnels uniquement** (hooks)
- Props : **typage TypeScript strict**
- Structure :
```
frontend/src/
├── components/    # composants réutilisables
├── pages/         # pages/routes
├── hooks/         # hooks custom
├── stores/        # Zustand stores
├── services/      # appels API
├── types/         # types TypeScript
└── utils/         # utilitaires
```

---

## 🧪 Tests

### Backend
- **Unitaires** : logique métier isolée (services/, utils/)
- **Intégration** : endpoints avec DB de test
- **Fixtures** : base de données PostgreSQL de test isolée
- Lancer : `pytest services/<name>/tests/ -v --cov`

### Frontend
- **Composants** : React Testing Library
- **E2E** : Playwright (Phase 2)

---

## 📚 Documentation API

Chaque service expose automatiquement :
- `GET /docs` → Swagger UI
- `GET /redoc` → ReDoc
- `GET /openapi.json` → schéma OpenAPI

---

## 👥 Contributeurs

Ce projet est développé et maintenu par ses contributeurs humains.
**Claude (Anthropic) n'est pas un contributeur de ce projet.**
Son usage est limité à l'assistance au développement, sous supervision et relecture experte à chaque étape.
