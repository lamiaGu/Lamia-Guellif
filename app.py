"""
Agent de veille académique — Interface Web
Université d'Ottawa | BCom Finance | Objectif 95%
"""

import json
import streamlit as st
import anthropic
from campus_agent import (
    load_data,
    save_data,
    execute_tool,
    compute_current_grade,
    compute_needed_grade,
    TOOLS,
)

# ─── Configuration de la page ─────────────────────────────────────────────────

st.set_page_config(
    page_title="Agent Académique — uOttawa BCom Finance",
    page_icon="🎓",
    layout="wide",
)

SYSTEM_PROMPT = """Tu es un agent de veille académique pour un étudiant en Baccalauréat en Commerce (spécialité Finance) à l'Université d'Ottawa.

Ton rôle est d'aider l'étudiant à atteindre un objectif de 95% dans tous ses cours.

Tes capacités :
- Consulter et mettre à jour les notes pour chaque évaluation
- Calculer la note nécessaire sur les évaluations restantes pour atteindre 95%
- Identifier les cours prioritaires selon l'urgence
- Donner des conseils d'étude personnalisés et motivants
- Suivre la progression globale

Règles importantes :
- Réponds toujours en français
- Sois encourageant mais réaliste sur l'atteinte des objectifs
- Utilise les outils disponibles pour obtenir des données à jour avant de répondre
- Quand tu affiches des notes, utilise toujours le symbole %
- Si une note requise dépasse 100%, sois honnête et propose des alternatives (parler au professeur, points bonus, etc.)
- Sois concis et précis dans tes réponses"""


# ─── Barre latérale ───────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🎓 Agent Académique")
    st.caption("Université d'Ottawa · BCom Finance")
    st.divider()

    api_key = st.text_input(
        "Clé API Anthropic",
        type="password",
        placeholder="sk-ant-...",
        help="Obtiens ta clé sur console.anthropic.com",
    )

    st.divider()

    # Tableau de bord rapide
    st.subheader("📊 Progression")
    data = load_data()
    courses = data["courses"]
    target = data["target_grade"]

    for c in courses:
        current = compute_current_grade(c["assessments"])
        completed = sum(1 for a in c["assessments"] if a["grade"] is not None)
        total = len(c["assessments"])

        if current is not None:
            color = "🟢" if current >= target else ("🟡" if current >= 85 else "🔴")
            st.write(f"{color} **{c['code']}** — {current:.1f}%")
            st.progress(completed / total, text=f"{completed}/{total} évaluations")
        else:
            st.write(f"⚪ **{c['code']}** — non commencé")

    st.divider()
    st.caption("💡 **Exemples de questions**")
    examples = [
        "Montre tous mes cours",
        "J'ai eu 88% au mi-session de ADM2340",
        "Que dois-je avoir sur le final de FIN3520?",
        "Quels cours prioriser?",
        "Quelle est ma moyenne générale?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True, key=f"ex_{ex}"):
            st.session_state.pending_input = ex


# ─── Zone principale ──────────────────────────────────────────────────────────

st.title("Agent de veille académique 📚")
st.caption(f"Objectif : **{target}%** par cours · {data['program']}")

# Initialisation de l'historique
if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage de l'historique
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
    elif msg["role"] == "assistant":
        with st.chat_message("assistant", avatar="🎓"):
            # Extraire le texte des blocs de contenu
            if isinstance(msg["content"], list):
                for block in msg["content"]:
                    if hasattr(block, "type") and block.type == "text":
                        st.write(block.text)
                    elif isinstance(block, dict) and block.get("type") == "text":
                        st.write(block["text"])
            else:
                st.write(msg["content"])


# ─── Entrée utilisateur ───────────────────────────────────────────────────────

# Gestion des boutons d'exemple
pending = st.session_state.pop("pending_input", None)
user_input = st.chat_input("Pose ta question à l'agent...") or pending

if user_input:
    if not api_key:
        st.error("Entre ta clé API Anthropic dans la barre latérale pour continuer.")
        st.stop()

    # Afficher le message utilisateur
    with st.chat_message("user"):
        st.write(user_input)

    st.session_state.messages.append({"role": "user", "content": user_input})

    # Appel à l'agent avec boucle d'outils
    client = anthropic.Anthropic(api_key=api_key)

    # Construire l'historique pour l'API (garder seulement texte pour messages passés)
    api_messages = []
    for msg in st.session_state.messages[:-1]:  # tous sauf le dernier
        if msg["role"] == "user":
            if isinstance(msg["content"], list):
                api_messages.append({"role": "user", "content": msg["content"]})
            else:
                api_messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            if isinstance(msg["content"], list):
                # Garder uniquement les blocs texte pour l'historique
                text_content = []
                for block in msg["content"]:
                    if hasattr(block, "type") and block.type == "text":
                        text_content.append({"type": "text", "text": block.text})
                    elif isinstance(block, dict) and block.get("type") == "text":
                        text_content.append(block)
                if text_content:
                    api_messages.append({"role": "assistant", "content": text_content})
            else:
                api_messages.append({"role": "assistant", "content": msg["content"]})
    api_messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant", avatar="🎓"):
        with st.spinner("Analyse en cours..."):
            try:
                final_text = ""
                while True:
                    response = client.messages.create(
                        model="claude-opus-4-6",
                        max_tokens=4096,
                        system=SYSTEM_PROMPT,
                        tools=TOOLS,
                        messages=api_messages,
                        thinking={"type": "adaptive"},
                    )

                    api_messages.append({"role": "assistant", "content": response.content})

                    if response.stop_reason == "end_turn":
                        break

                    if response.stop_reason == "tool_use":
                        tool_results = []
                        for block in response.content:
                            if block.type == "tool_use":
                                result = execute_tool(block.name, block.input)
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": json.dumps(result, ensure_ascii=False),
                                })
                        api_messages.append({"role": "user", "content": tool_results})
                    else:
                        break

                # Afficher la réponse finale
                for block in response.content:
                    if block.type == "text" and block.text.strip():
                        st.write(block.text)
                        final_text = block.text

                # Sauvegarder dans l'historique
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response.content,
                })

                # Rafraîchir la sidebar (progression mise à jour)
                st.rerun()

            except anthropic.AuthenticationError:
                st.error("Clé API invalide. Vérifie ta clé dans la barre latérale.")
            except Exception as e:
                st.error(f"Erreur : {e}")
