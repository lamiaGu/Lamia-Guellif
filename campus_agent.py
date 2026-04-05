#!/usr/bin/env python3
"""
Agent de veille académique - Université d'Ottawa
Baccalauréat en Commerce, spécialité Finance
Objectif : 95% par cours
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

DATA_FILE = Path(__file__).parent / "data" / "courses.json"


# ─── Fonctions utilitaires ────────────────────────────────────────────────────

def load_data() -> dict:
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def compute_current_grade(assessments: list[dict]) -> float | None:
    """Note actuelle pondérée sur les évaluations complétées."""
    completed = [(a["grade"], a["weight"]) for a in assessments if a["grade"] is not None]
    if not completed:
        return None
    total_weight = sum(w for _, w in completed)
    weighted_sum = sum(g * w for g, w in completed)
    return round(weighted_sum / total_weight, 2)


def compute_needed_grade(assessments: list[dict], target: float) -> float | None:
    """Note requise sur les évaluations restantes pour atteindre la cible."""
    done_weight = sum(a["weight"] for a in assessments if a["grade"] is not None)
    done_score = sum(a["grade"] * a["weight"] for a in assessments if a["grade"] is not None)
    remaining_weight = sum(a["weight"] for a in assessments if a["grade"] is None)

    if remaining_weight == 0:
        return None  # Tout est complété

    needed = (target * 100 - done_score) / remaining_weight
    return round(needed, 2)


def course_summary(course: dict, target: float) -> dict:
    assessments = course["assessments"]
    current = compute_current_grade(assessments)
    needed = compute_needed_grade(assessments, target)
    completed = sum(1 for a in assessments if a["grade"] is not None)
    total = len(assessments)
    return {
        "code": course["code"],
        "name": course["name"],
        "current_grade": current,
        "needed_grade": needed,
        "completed": completed,
        "total": total,
        "status": "terminé" if completed == total else "en cours" if completed > 0 else "non commencé",
    }


# ─── Outils de l'agent ───────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "get_all_courses",
        "description": "Obtient la liste complète des cours avec leur progression et les notes actuelles.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_course_details",
        "description": "Obtient les détails complets d'un cours : toutes les évaluations, notes, et calculs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "course_code": {
                    "type": "string",
                    "description": "Le code du cours (ex: ADM1100, FIN3520)",
                }
            },
            "required": ["course_code"],
        },
    },
    {
        "name": "update_grade",
        "description": "Enregistre ou met à jour la note d'une évaluation spécifique dans un cours.",
        "input_schema": {
            "type": "object",
            "properties": {
                "course_code": {"type": "string", "description": "Code du cours"},
                "assessment_name": {
                    "type": "string",
                    "description": "Nom exact de l'évaluation",
                },
                "grade": {
                    "type": "number",
                    "description": "Note obtenue en pourcentage (0-100)",
                },
            },
            "required": ["course_code", "assessment_name", "grade"],
        },
    },
    {
        "name": "get_grade_projection",
        "description": "Calcule la note minimale requise sur chaque évaluation restante pour atteindre 95%.",
        "input_schema": {
            "type": "object",
            "properties": {
                "course_code": {
                    "type": "string",
                    "description": "Code du cours (optionnel - tous les cours si absent)",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_study_recommendations",
        "description": "Génère des recommandations d'étude personnalisées basées sur la progression actuelle.",
        "input_schema": {
            "type": "object",
            "properties": {
                "course_code": {
                    "type": "string",
                    "description": "Code du cours (optionnel)",
                }
            },
            "required": [],
        },
    },
    {
        "name": "add_course",
        "description": "Ajoute un nouveau cours au suivi.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code du cours (ex: FIN4200)"},
                "name": {"type": "string", "description": "Nom complet du cours"},
                "credits": {"type": "integer", "description": "Nombre de crédits"},
                "semester": {"type": "string", "description": "Semestre (ex: A3, H2)"},
                "assessments": {
                    "type": "array",
                    "description": "Liste des évaluations avec nom et poids",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "weight": {"type": "number"},
                        },
                        "required": ["name", "weight"],
                    },
                },
            },
            "required": ["code", "name", "credits", "semester", "assessments"],
        },
    },
    {
        "name": "get_overall_gpa",
        "description": "Calcule la moyenne générale pondérée sur tous les cours avec notes.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


# ─── Exécution des outils ─────────────────────────────────────────────────────

def execute_tool(name: str, inputs: dict) -> Any:
    data = load_data()
    target = data["target_grade"]
    courses = data["courses"]

    if name == "get_all_courses":
        summaries = [course_summary(c, target) for c in courses]
        return {
            "program": data["program"],
            "target_grade": target,
            "courses": summaries,
        }

    elif name == "get_course_details":
        code = inputs["course_code"].upper()
        course = next((c for c in courses if c["code"] == code), None)
        if not course:
            return {"error": f"Cours {code} introuvable."}
        summary = course_summary(course, target)
        return {**summary, "assessments": course["assessments"]}

    elif name == "update_grade":
        code = inputs["course_code"].upper()
        assessment_name = inputs["assessment_name"]
        grade = float(inputs["grade"])

        if not 0 <= grade <= 100:
            return {"error": "La note doit être entre 0 et 100."}

        course = next((c for c in courses if c["code"] == code), None)
        if not course:
            return {"error": f"Cours {code} introuvable."}

        assessment = next(
            (a for a in course["assessments"] if a["name"].lower() == assessment_name.lower()),
            None,
        )
        if not assessment:
            available = [a["name"] for a in course["assessments"]]
            return {"error": f"Évaluation '{assessment_name}' introuvable. Disponibles: {available}"}

        old_grade = assessment["grade"]
        assessment["grade"] = grade
        save_data(data)

        summary = course_summary(course, target)
        return {
            "success": True,
            "course": code,
            "assessment": assessment["name"],
            "old_grade": old_grade,
            "new_grade": grade,
            "current_course_grade": summary["current_grade"],
            "needed_on_remaining": summary["needed_grade"],
        }

    elif name == "get_grade_projection":
        code = inputs.get("course_code", "").upper()
        if code:
            course = next((c for c in courses if c["code"] == code), None)
            if not course:
                return {"error": f"Cours {code} introuvable."}
            target_courses = [course]
        else:
            target_courses = courses

        projections = []
        for c in target_courses:
            assessments = c["assessments"]
            remaining = [a for a in assessments if a["grade"] is None]
            needed = compute_needed_grade(assessments, target)
            current = compute_current_grade(assessments)
            projections.append({
                "code": c["code"],
                "name": c["name"],
                "current_grade": current,
                "needed_average_on_remaining": needed,
                "remaining_assessments": remaining,
                "feasible": needed is None or needed <= 100,
            })
        return {"target": target, "projections": projections}

    elif name == "get_study_recommendations":
        code = inputs.get("course_code", "").upper()
        if code:
            target_courses = [c for c in courses if c["code"] == code]
        else:
            target_courses = courses

        recs = []
        for c in target_courses:
            summary = course_summary(c, target)
            needed = summary["needed_grade"]
            current = summary["current_grade"]

            if needed is None and current is not None:
                if current >= target:
                    priority = "objectif_atteint"
                    advice = "Excellent! Continue à maintenir ce niveau."
                else:
                    priority = "terminé_sous_cible"
                    advice = f"Cours terminé à {current}% (cible: {target}%). Rien à faire."
            elif needed is None:
                priority = "non_commencé"
                advice = "Commence dès maintenant pour établir un rythme d'étude."
            elif needed > 100:
                priority = "critique"
                advice = f"Score parfait requis (>100%) - revoir la stratégie avec le professeur."
            elif needed > 90:
                priority = "haute"
                advice = f"Il te faut {needed}% sur les évaluations restantes. Intensifie les révisions."
            elif needed > 80:
                priority = "moyenne"
                advice = f"Il te faut {needed}% sur les évaluations restantes. Maintiens le rythme."
            else:
                priority = "bonne_progression"
                advice = f"Bonne progression! Il te faut seulement {needed}% sur les évaluations restantes."

            recs.append({
                "code": c["code"],
                "name": c["name"],
                "priority": priority,
                "advice": advice,
                "current_grade": current,
                "needed_grade": needed,
                "remaining_assessments": [a["name"] for a in c["assessments"] if a["grade"] is None],
            })

        recs.sort(key=lambda x: {"critique": 0, "haute": 1, "moyenne": 2, "non_commencé": 3, "bonne_progression": 4, "objectif_atteint": 5, "terminé_sous_cible": 6}.get(x["priority"], 7))
        return {"recommendations": recs}

    elif name == "add_course":
        code = inputs["code"].upper()
        if any(c["code"] == code for c in courses):
            return {"error": f"Le cours {code} existe déjà."}

        new_course = {
            "code": code,
            "name": inputs["name"],
            "credits": inputs["credits"],
            "semester": inputs["semester"],
            "assessments": [
                {"name": a["name"], "weight": a["weight"], "grade": None}
                for a in inputs["assessments"]
            ],
        }
        data["courses"].append(new_course)
        save_data(data)
        return {"success": True, "message": f"Cours {code} ajouté avec succès.", "course": new_course}

    elif name == "get_overall_gpa":
        graded_courses = []
        for c in courses:
            current = compute_current_grade(c["assessments"])
            if current is not None:
                graded_courses.append({
                    "code": c["code"],
                    "name": c["name"],
                    "credits": c["credits"],
                    "grade": current,
                })

        if not graded_courses:
            return {"error": "Aucune note enregistrée pour le moment."}

        total_credits = sum(c["credits"] for c in graded_courses)
        weighted_sum = sum(c["grade"] * c["credits"] for c in graded_courses)
        gpa = round(weighted_sum / total_credits, 2) if total_credits > 0 else 0

        return {
            "overall_gpa": gpa,
            "target": target,
            "gap": round(target - gpa, 2),
            "courses_graded": len(graded_courses),
            "total_courses": len(courses),
            "details": graded_courses,
        }

    return {"error": f"Outil inconnu: {name}"}


# ─── Interface Rich ───────────────────────────────────────────────────────────

def display_welcome():
    console.print(Panel(
        Text.assemble(
            ("Agent de veille académique\n", "bold cyan"),
            ("Université d'Ottawa — BCom Finance\n", "white"),
            ("Objectif: 95% par cours", "bold yellow"),
        ),
        border_style="cyan",
        padding=(1, 2),
    ))
    console.print("[dim]Commandes: 'quitter' ou 'exit' pour terminer | 'aide' pour les exemples[/dim]\n")


def display_help():
    table = Table(title="Exemples de questions", border_style="blue", show_lines=True)
    table.add_column("Question", style="white")
    table.add_column("Description", style="dim")

    examples = [
        ("Montre-moi tous mes cours", "Vue d'ensemble de la progression"),
        ("Quelle est ma note actuelle en FIN3520?", "Détails d'un cours spécifique"),
        ("J'ai eu 88% à l'examen mi-session de ADM2340", "Enregistrer une note"),
        ("Quelle note dois-je avoir sur le final de ADM3360?", "Projection de notes"),
        ("Quels cours dois-je prioriser?", "Recommandations de révision"),
        ("Quelle est ma moyenne générale?", "GPA pondéré"),
        ("Ajoute le cours FIN4200 Gestion des risques", "Ajouter un cours"),
    ]

    for q, d in examples:
        table.add_row(q, d)

    console.print(table)
    console.print()


# ─── Boucle principale ────────────────────────────────────────────────────────

def run_agent():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]Erreur: La variable ANTHROPIC_API_KEY n'est pas définie.[/red]")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = """Tu es un agent de veille académique pour un étudiant en Baccalauréat en Commerce (spécialité Finance) à l'Université d'Ottawa.

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
- Si une note requise dépasse 100%, sois honnête et propose des alternatives (parler au professeur, bonus, etc.)
- Sois concis et précis dans tes réponses"""

    messages = []
    display_welcome()

    while True:
        try:
            user_input = console.input("[bold cyan]Toi:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]À bientôt![/yellow]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quitter", "exit", "quit"):
            console.print("[yellow]À bientôt! Bon courage pour tes études![/yellow]")
            break

        if user_input.lower() in ("aide", "help"):
            display_help()
            continue

        messages.append({"role": "user", "content": user_input})

        # Boucle d'agent avec outils
        with console.status("[dim]Analyse en cours...[/dim]", spinner="dots"):
            while True:
                response = client.messages.create(
                    model="claude-opus-4-6",
                    max_tokens=4096,
                    system=system_prompt,
                    tools=TOOLS,
                    messages=messages,
                    thinking={"type": "adaptive"},
                )

                # Ajoute la réponse de l'assistant à l'historique
                messages.append({"role": "assistant", "content": response.content})

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

                    messages.append({"role": "user", "content": tool_results})
                else:
                    break

        # Affiche la réponse finale
        for block in response.content:
            if block.type == "text" and block.text.strip():
                console.print(Panel(
                    block.text,
                    title="[bold green]Agent[/bold green]",
                    border_style="green",
                    padding=(0, 1),
                ))
        console.print()


if __name__ == "__main__":
    run_agent()
