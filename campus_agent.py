"""
Logique de l'agent académique — multi-utilisateur
"""

import json
import shutil
from pathlib import Path
from typing import Any

TEMPLATE_FILE = Path(__file__).parent / "data" / "template.json"
USERS_DIR = Path(__file__).parent / "data" / "users"

TOOLS = [
    {
        "name": "get_all_courses",
        "description": "Obtient la liste complète des cours avec progression et notes actuelles.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_course_details",
        "description": "Obtient les détails complets d'un cours : évaluations, notes, calculs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "course_code": {"type": "string", "description": "Code du cours (ex: ADM1100)"}
            },
            "required": ["course_code"],
        },
    },
    {
        "name": "update_grade",
        "description": "Enregistre ou met à jour la note d'une évaluation dans un cours.",
        "input_schema": {
            "type": "object",
            "properties": {
                "course_code": {"type": "string"},
                "assessment_name": {"type": "string", "description": "Nom exact de l'évaluation"},
                "grade": {"type": "number", "description": "Note en pourcentage (0-100)"},
            },
            "required": ["course_code", "assessment_name", "grade"],
        },
    },
    {
        "name": "get_grade_projection",
        "description": "Calcule la note minimale requise sur les évaluations restantes pour atteindre 95%.",
        "input_schema": {
            "type": "object",
            "properties": {
                "course_code": {"type": "string", "description": "Code du cours (optionnel — tous si absent)"}
            },
            "required": [],
        },
    },
    {
        "name": "get_study_recommendations",
        "description": "Génère des recommandations d'étude priorisées selon la progression actuelle.",
        "input_schema": {
            "type": "object",
            "properties": {
                "course_code": {"type": "string", "description": "Code du cours (optionnel)"}
            },
            "required": [],
        },
    },
    {
        "name": "get_overall_gpa",
        "description": "Calcule la moyenne générale pondérée sur tous les cours notés.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "add_course",
        "description": "Ajoute un nouveau cours au suivi.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "name": {"type": "string"},
                "credits": {"type": "integer"},
                "semester": {"type": "string"},
                "assessments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}, "weight": {"type": "number"}},
                        "required": ["name", "weight"],
                    },
                },
            },
            "required": ["code", "name", "credits", "semester", "assessments"],
        },
    },
]

SYSTEM_PROMPT = """Tu es un agent de veille académique pour un étudiant en Baccalauréat en Commerce (spécialité Finance) à l'Université d'Ottawa.

Ton rôle : aider l'étudiant à atteindre 95% dans tous ses cours.

Capacités :
- Consulter et mettre à jour les notes pour chaque évaluation
- Calculer la note nécessaire sur les évaluations restantes pour atteindre 95%
- Identifier les cours prioritaires
- Donner des conseils d'étude personnalisés et motivants
- Suivre la progression globale

Règles :
- Réponds toujours en français
- Sois encourageant mais réaliste
- Utilise les outils avant de répondre
- Si une note requise dépasse 100%, propose des alternatives (bonus, parler au professeur)
- Réponds en Markdown pour une belle mise en page"""


# ─── Gestion des fichiers par utilisateur ─────────────────────────────────────

def get_user_file(session_id: str) -> Path:
    USERS_DIR.mkdir(parents=True, exist_ok=True)
    user_file = USERS_DIR / f"{session_id}.json"
    if not user_file.exists():
        shutil.copy(TEMPLATE_FILE, user_file)
    return user_file


def load_data(session_id: str) -> dict:
    with open(get_user_file(session_id), encoding="utf-8") as f:
        return json.load(f)


def save_data(data: dict, session_id: str) -> None:
    with open(get_user_file(session_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── Calculs ──────────────────────────────────────────────────────────────────

def compute_current_grade(assessments: list) -> float | None:
    completed = [(a["grade"], a["weight"]) for a in assessments if a["grade"] is not None]
    if not completed:
        return None
    total_w = sum(w for _, w in completed)
    return round(sum(g * w for g, w in completed) / total_w, 2)


def compute_needed_grade(assessments: list, target: float) -> float | None:
    done_score = sum(a["grade"] * a["weight"] for a in assessments if a["grade"] is not None)
    remaining_w = sum(a["weight"] for a in assessments if a["grade"] is None)
    if remaining_w == 0:
        return None
    return round((target * 100 - done_score) / remaining_w, 2)


def course_summary(course: dict, target: float) -> dict:
    assessments = course["assessments"]
    current = compute_current_grade(assessments)
    needed = compute_needed_grade(assessments, target)
    completed = sum(1 for a in assessments if a["grade"] is not None)
    return {
        "code": course["code"],
        "name": course["name"],
        "current_grade": current,
        "needed_grade": needed,
        "completed": completed,
        "total": len(assessments),
    }


# ─── Exécution des outils ─────────────────────────────────────────────────────

def execute_tool(name: str, inputs: dict, session_id: str) -> Any:
    data = load_data(session_id)
    target = data["target_grade"]
    courses = data["courses"]

    if name == "get_all_courses":
        return {
            "program": data["program"],
            "target_grade": target,
            "courses": [course_summary(c, target) for c in courses],
        }

    elif name == "get_course_details":
        code = inputs["course_code"].upper()
        course = next((c for c in courses if c["code"] == code), None)
        if not course:
            return {"error": f"Cours {code} introuvable."}
        return {**course_summary(course, target), "assessments": course["assessments"]}

    elif name == "update_grade":
        code = inputs["course_code"].upper()
        grade = float(inputs["grade"])
        if not 0 <= grade <= 100:
            return {"error": "La note doit être entre 0 et 100."}
        course = next((c for c in courses if c["code"] == code), None)
        if not course:
            return {"error": f"Cours {code} introuvable."}
        assessment = next(
            (a for a in course["assessments"] if a["name"].lower() == inputs["assessment_name"].lower()),
            None,
        )
        if not assessment:
            return {"error": f"Évaluation introuvable. Disponibles: {[a['name'] for a in course['assessments']]}"}
        assessment["grade"] = grade
        save_data(data, session_id)
        summary = course_summary(course, target)
        return {
            "success": True,
            "course": code,
            "assessment": assessment["name"],
            "new_grade": grade,
            "current_course_grade": summary["current_grade"],
            "needed_on_remaining": summary["needed_grade"],
        }

    elif name == "get_grade_projection":
        code = inputs.get("course_code", "").upper()
        target_courses = [c for c in courses if c["code"] == code] if code else courses
        if code and not target_courses:
            return {"error": f"Cours {code} introuvable."}
        projections = []
        for c in target_courses:
            needed = compute_needed_grade(c["assessments"], target)
            projections.append({
                "code": c["code"],
                "name": c["name"],
                "current_grade": compute_current_grade(c["assessments"]),
                "needed_average_on_remaining": needed,
                "remaining_assessments": [a for a in c["assessments"] if a["grade"] is None],
                "feasible": needed is None or needed <= 100,
            })
        return {"target": target, "projections": projections}

    elif name == "get_study_recommendations":
        code = inputs.get("course_code", "").upper()
        target_courses = [c for c in courses if c["code"] == code] if code else courses
        recs = []
        for c in target_courses:
            summary = course_summary(c, target)
            needed = summary["needed_grade"]
            current = summary["current_grade"]
            if needed is None and current is not None:
                priority = "objectif_atteint" if current >= target else "terminé_sous_cible"
                advice = "Excellent! Objectif atteint." if current >= target else f"Cours terminé à {current}%."
            elif needed is None:
                priority = "non_commencé"
                advice = "Commence dès maintenant pour établir un rythme."
            elif needed > 100:
                priority = "critique"
                advice = f"Score > 100% requis. Contacte ton professeur pour des options."
            elif needed > 90:
                priority = "haute"
                advice = f"Il te faut {needed}% sur le reste. Intensifie les révisions."
            elif needed > 80:
                priority = "moyenne"
                advice = f"Il te faut {needed}% sur le reste. Maintiens le rythme."
            else:
                priority = "bonne_progression"
                advice = f"Bonne progression! Seulement {needed}% requis sur le reste."
            recs.append({
                "code": c["code"],
                "name": c["name"],
                "priority": priority,
                "advice": advice,
                "current_grade": current,
                "needed_grade": needed,
                "remaining": [a["name"] for a in c["assessments"] if a["grade"] is None],
            })
        order = {"critique": 0, "haute": 1, "moyenne": 2, "non_commencé": 3, "bonne_progression": 4, "objectif_atteint": 5, "terminé_sous_cible": 6}
        recs.sort(key=lambda x: order.get(x["priority"], 7))
        return {"recommendations": recs}

    elif name == "get_overall_gpa":
        graded = [{"code": c["code"], "name": c["name"], "credits": c["credits"], "grade": compute_current_grade(c["assessments"])}
                  for c in courses if compute_current_grade(c["assessments"]) is not None]
        if not graded:
            return {"error": "Aucune note enregistrée."}
        total_credits = sum(c["credits"] for c in graded)
        gpa = round(sum(c["grade"] * c["credits"] for c in graded) / total_credits, 2)
        return {"overall_gpa": gpa, "target": target, "gap": round(target - gpa, 2), "details": graded}

    elif name == "add_course":
        code = inputs["code"].upper()
        if any(c["code"] == code for c in courses):
            return {"error": f"Le cours {code} existe déjà."}
        new_course = {
            "code": code, "name": inputs["name"], "credits": inputs["credits"],
            "semester": inputs["semester"],
            "assessments": [{"name": a["name"], "weight": a["weight"], "grade": None} for a in inputs["assessments"]],
        }
        data["courses"].append(new_course)
        save_data(data, session_id)
        return {"success": True, "course": new_course}

    return {"error": f"Outil inconnu: {name}"}
