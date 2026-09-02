# LogAI : CLI Copilot d'Analyse de Logs par IA

**LogAI** est un outil en ligne de commande (CLI) développé en Python. Il utilise les API d'IA générative (Gemini/ OpenAI / Anthropic Claude) pour analyser automatiquement des fichiers de logs complexes, détecter les anomalies, expliquer la cause racine des erreurs et proposer des correctifs en temps réel.

---

## Cas d'usage & Fonctionnalités

- **Analyse d'incidents rapide :** Traitement de fichiers `.log` volumineux sans lecture manuelle.
- **Rapport synthétique structuré :** Analyse du niveau de gravité (INFO, WARN, ERROR, CRITICAL), résumé des causes et propositions de correctifs.
- **Sortie Terminal UI :** Affichage élégant et lisible directement dans la console via la librairie `rich`.
- **Export multi-format :** Génération de rapports au format Markdown ou JSON pour intégration dans un workflow CI/CD ou Ticketing.

---

## Architecture & Stack Technique

- **Langage :** Python 3.10+
- **CLI Framework :** `argparse` / `click`
- **IA / LLM Integration :** `openai` (Structured Outputs) / Anthropic SDK
- **Data & Parsing :** `pydantic` (Validation et typage strict du JSON de sortie)
- **Formatting UI :** `rich`

---

## Installation & Configuration

### 1. Prérequis
- Python 3.10 ou supérieur
- Une clé API OpenAI (`OPENAI_API_KEY`) ou Anthropic (`ANTHROPIC_API_KEY`)

### 2. Cloner le projet et installer les dépendances

```bash
git clone [https://github.com/ton-profil/logai-cli.git](https://github.com/ton-profil/logai-cli.git)
cd logai-cli

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
