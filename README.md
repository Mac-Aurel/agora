# Agora - Plateforme de Connaissance Collaborative

> *La place publique de la connaissance*

Plateforme open source de connaissance collaborative pour chercheurs, étudiants et curieux.

---

## Prérequis

- [Docker](https://docs.docker.com/get-docker/) ≥ 24
- [Docker Compose](https://docs.docker.com/compose/install/) ≥ 2.20

---

## Lancer le projet en local

### 1. Configurer l'environnement

```bash
cp .env.example .env
```

Éditez `.env` et remplacez toutes les valeurs `changeme` :

| Variable | Description |
|---|---|
| `POSTGRES_PASSWORD` | Mot de passe PostgreSQL |
| `MINIO_ROOT_PASSWORD` | Mot de passe MinIO |
| `JWT_SECRET` | Clé secrète 256 bits (`openssl rand -hex 32`) |
| `YOUTUBE_API_KEY` | Clé API YouTube Data v3 (facultatif en phase MVP) |

### 2. Lancer tous les services

```bash
docker-compose up --build
```

> **Note :** Les services backend exposent uniquement un endpoint `/health` à ce stade.
> Les `requirements.txt` sont vides et doivent être complétés avant d'implémenter la logique métier.
> Voir `AGORA.md` pour la roadmap et les conventions de développement.

---

## Services disponibles

| Service | URL | Description |
|---|---|---|
| **Gateway** | http://localhost:8000 | Point d'entrée API |
| **Auth** | http://localhost:8001/docs | Authentification + JWT |
| **Boards** | http://localhost:8002/docs | Boards et contributions |
| **Content** | http://localhost:8003/docs | Upload et stockage |
| **Ingestion** | http://localhost:8004/docs | Pipeline parsing |
| **Search** | http://localhost:8005/docs | Recherche RAG |
| **Discovery** | http://localhost:8006/docs | Suggestions externes |
| **Frontend** | http://localhost:3000 | Interface utilisateur |
| **MinIO Console** | http://localhost:9001 | Administration stockage |
| **ChromaDB** | http://localhost:8888 | Base vectorielle |

---

## Structure du projet

```
agora/
├── services/
│   ├── gateway/     # Port 8000 — Point d'entrée, routing, auth middleware
│   ├── auth/        # Port 8001 — Authentification username/password + JWT
│   ├── boards/      # Port 8002 — CRUD boards, contributions, connexions
│   ├── content/     # Port 8003 — Upload fichiers, stockage MinIO
│   ├── ingestion/   # Port 8004 — Pipeline parsing multi-format (Redis queue)
│   ├── search/      # Port 8005 — RAG, embeddings, ChromaDB, Q&A
│   └── discovery/   # Port 8006 — Suggestions via APIs publiques
├── frontend/        # React 18 + Vite + TypeScript + TailwindCSS
├── shared/          # Schémas Pydantic partagés, utils communs
├── infra/           # Configs Nginx, scripts
├── docs/            # Documentation technique
├── tests/           # Tests d'intégration inter-services
├── docker-compose.yml
├── .env.example
└── README.md
```

Chaque service backend suit la structure :

```
services/<name>/
├── app/
│   ├── main.py          # FastAPI app, lifespan, middleware
│   ├── config.py        # Settings via Pydantic BaseSettings
│   ├── dependencies.py  # Dépendances FastAPI (get_db, get_current_user)
│   ├── models/          # Modèles SQLAlchemy
│   ├── schemas/         # Schémas Pydantic (request/response)
│   ├── routers/         # Endpoints FastAPI
│   ├── services/        # Logique métier
│   └── utils/           # Utilitaires
├── tests/
├── Dockerfile
└── requirements.txt
```

---

## Commandes utiles

```bash
# Arrêter les services
docker-compose down

# Arrêter et supprimer les volumes (reset complet)
docker-compose down -v

# Logs d'un service spécifique
docker-compose logs -f auth

# Relancer un service après modification
docker-compose up --build auth

# Vérifier la santé des services
docker-compose ps
```

---

## Réseau Docker

Tous les services communiquent sur le réseau interne `agora-network`.
Les services ne doivent **jamais** accéder aux autres services via les ports hôtes.

| Service | Adresse interne |
|---|---|
| PostgreSQL | `postgres:5432` |
| Redis | `redis:6379` |
| ChromaDB | `chromadb:8000` |
| MinIO | `minio:9000` |
| Auth | `auth:8000` |
| Boards | `boards:8000` |
| Content | `content:8000` |
| Ingestion | `ingestion:8000` |
| Search | `search:8000` |
| Discovery | `discovery:8000` |

---

Voir `AGORA.md` pour la roadmap complète, les modèles de données, et les conventions de code.
