# Agent de veille académique — uOttawa BCom Finance

> Agent IA conversationnel pour atteindre **95% par cours**.
> Interface web moderne, accessible depuis n'importe quel appareil (téléphone, tablette, ordinateur).

---

## Déploiement en 3 minutes sur Railway (lien URL public)

Railway est la façon la plus simple d'obtenir un lien URL public pour partager l'app.

### Étape 1 — Déployer

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

1. Va sur **[railway.app](https://railway.app)** → "New Project" → "Deploy from GitHub repo"
2. Sélectionne ce dépôt (`lamiaGu/Lamia-Guellif`)
3. Dans les variables d'environnement, ajoute :
   ```
   ANTHROPIC_API_KEY = sk-ant-...
   ```
4. La commande de démarrage est détectée automatiquement via `Procfile`

### Étape 2 — Partager le lien

Railway génère un lien public comme `https://ton-app.railway.app`.
Partage ce lien — accessible sur téléphone, tablette, ordinateur.

---

## Autres options de déploiement

### Render (gratuit)
1. Va sur [render.com](https://render.com) → "New Web Service"
2. Connecte ce dépôt GitHub
3. Build command : `pip install -r requirements.txt`
4. Start command : `uvicorn server:app --host 0.0.0.0 --port $PORT`
5. Ajoute la variable d'env `ANTHROPIC_API_KEY`

### En local
```bash
git clone https://github.com/lamiaGu/Lamia-Guellif.git
cd Lamia-Guellif
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
uvicorn server:app --reload
# Ouvre http://localhost:8000
```

---

## Architecture

```
├── server.py           # Backend FastAPI (API + streaming SSE)
├── campus_agent.py     # Logique de l'agent et outils
├── static/
│   └── index.html      # Interface web (dark theme, chat en temps réel)
├── data/
│   ├── template.json   # Modèle de cours par défaut
│   └── users/          # Données isolées par étudiant (auto-créées)
├── Procfile            # Commande de démarrage (Railway/Render)
└── requirements.txt
```

**Isolation des données** : chaque étudiant obtient automatiquement ses propres données via un identifiant de session stocké dans son navigateur. Pas de compte requis.

---

## Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| Chat en temps réel | Réponses streamées mot par mot |
| Suivi des notes | Enregistre chaque évaluation par cours |
| Projection 95% | Calcule la note requise sur le reste |
| Priorités | Identifie les cours les plus urgents |
| Tableau de bord | Barres de progression en sidebar |
| Multi-utilisateur | Données isolées par navigateur |
| Mobile friendly | Fonctionne sur téléphone |
