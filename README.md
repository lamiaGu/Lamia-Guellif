# Agent de veille académique — uOttawa BCom Finance

> Agent IA conversationnel pour atteindre **95% par cours** en Baccalauréat en Commerce, spécialité Finance, à l'Université d'Ottawa.

---

## Utilisation rapide (navigateur)

### Option 1 — Streamlit Cloud (recommandé, aucune installation)

1. Va sur [streamlit.io/cloud](https://streamlit.io/cloud)
2. Connecte ton compte GitHub
3. Déploie ce dépôt → l'app tourne dans le cloud
4. Partage le lien à tes collègues

### Option 2 — En local (5 minutes)

```bash
# 1. Cloner le dépôt
git clone https://github.com/lamiaGu/Lamia-Guellif.git
cd Lamia-Guellif

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Lancer l'interface web
streamlit run app.py
```

L'application s'ouvre automatiquement dans ton navigateur sur `http://localhost:8501`.

---

## Clé API requise

L'agent utilise Claude (Anthropic). Chaque étudiant entre sa propre clé :

1. Créer un compte sur [console.anthropic.com](https://console.anthropic.com)
2. Générer une clé API (gratuit pour commencer)
3. La coller dans la barre latérale de l'application

---

## Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| Suivi des notes | Enregistre chaque évaluation (examen, devoir, projet) |
| Projection 95% | Calcule la note requise sur chaque évaluation restante |
| Priorités | Identifie les cours les plus urgents |
| Recommandations | Conseils d'étude personnalisés |
| Moyenne générale | GPA pondéré sur tous les cours notés |
| Ajout de cours | Personnalise les cours selon ton programme réel |

## Cours inclus par défaut

| Code | Cours |
|---|---|
| ADM1100 | Introduction aux affaires en contexte mondial |
| ADM2340 | Comptabilité financière |
| ADM2350 | Comptabilité de gestion |
| ADM3360 | Finance d'entreprise |
| ADM3380 | Marchés financiers |
| FIN3520 | Placements |
| FIN4135 | Analyse des états financiers |
| ECO1104 | Introduction à la microéconomie |
| ECO1504 | Introduction à la macroéconomie |
| MAT2377 | Probabilités et statistiques |

---

## Exemples de questions

- *"Montre-moi tous mes cours"*
- *"J'ai eu 88% à l'examen mi-session de ADM2340"*
- *"Quelle note dois-je avoir sur le final de FIN3520 pour avoir 95% ?"*
- *"Quels cours dois-je prioriser cette semaine ?"*
- *"Quelle est ma moyenne générale ?"*

---

## Structure du projet

```
├── app.py              # Interface web (Streamlit)
├── campus_agent.py     # Logique de l'agent et outils
├── data/
│   └── courses.json    # Cours et notes (modifiable)
└── requirements.txt    # Dépendances Python
```
