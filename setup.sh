#!/bin/bash
# Installation et lancement de l'agent de veille académique

echo "Installation des dépendances..."
pip install -r requirements.txt

echo ""
echo "Pour lancer l'agent :"
echo "  export ANTHROPIC_API_KEY='votre-clé-api'"
echo "  python campus_agent.py"
