"""
Planificateur automatique
Fichier : backend/scheduler.py

Ce script tourne en arrière-plan et :
  - Collecte les nouveaux posts toutes les heures
  - Lance l'analyse NLP automatiquement
  - Génère les alertes si nécessaire
  - Affiche un rapport dans le terminal

Pour démarrer :
    python backend/scheduler.py

Pour arrêter :
    Ctrl+C
"""

import schedule
import time
import sys
import os
from datetime import datetime

# Charger les variables d'environnement
from dotenv import load_dotenv
load_dotenv()

# Ajouter le dossier backend au path
sys.path.insert(0, os.path.dirname(__file__))

from models import init_database, get_stats_summary
from collectors.collector import run_all_collectors
from nlp.analyzer import run_analysis_pipeline


def print_banner():
    print("""
╔══════════════════════════════════════════════╗
║        SocialMonitor — Planificateur         ║
║     Analyse automatique toutes les heures    ║
╚══════════════════════════════════════════════╝
    """)


def print_report():
    """Affiche un rapport résumé dans le terminal."""
    try:
        data = get_stats_summary()
        stats = data["stats"]
        total = stats["total"] or 0
        pos = stats["positive"] or 0
        neg = stats["negative"] or 0

        print(f"\n{'─'*50}")
        print(f"  RAPPORT — {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
        print(f"{'─'*50}")
        print(f"  Total posts analysés : {total}")
        if total > 0:
            print(f"  Positifs : {pos} ({round(pos/total*100)}%)")
            print(f"  Négatifs : {neg} ({round(neg/total*100)}%)")
        print(f"  Alertes actives : {len(data['alerts'])}")
        if data["subjects"]:
            print(f"  Sujet dominant  : {data['subjects'][0]['subject']}")
        if data["alerts"]:
            print(f"\n  ⚠️  ALERTES :")
            for a in data["alerts"]:
                print(f"     [{a['severity'].upper()}] {a['message']}")
        print(f"{'─'*50}\n")
    except Exception as e:
        print(f"[RAPPORT] Erreur : {e}")


def run_cycle():
    """
    Un cycle complet :
    1. Collecte les nouveaux posts
    2. Analyse avec NLP
    3. Affiche le rapport
    """
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Démarrage du cycle d'analyse...")

    # Étape 1 — Collecte
    # use_manual=False pour ne pas réinsérer les posts de test en boucle
    # Passe à True uniquement pour tester
    run_all_collectors(use_manual=False)

    # Étape 2 — Analyse NLP
    run_analysis_pipeline()

    # Étape 3 — Rapport
    print_report()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Cycle terminé. Prochain cycle dans 1 heure.")


# ─────────────────────────────────────────────
#  DÉMARRAGE
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print_banner()

    # Initialiser la base de données
    init_database()

    # Lancer un premier cycle immédiatement au démarrage
    print("[PLANIFICATEUR] Premier cycle au démarrage...")
    run_cycle()

    # Planifier les cycles suivants
    schedule.every(1).hour.do(run_cycle)       # Toutes les heures
    # schedule.every(30).minutes.do(run_cycle) # Toutes les 30 min (décommenter si besoin)
    # schedule.every().day.at("08:00").do(run_cycle) # Chaque jour à 8h (décommenter si besoin)

    print(f"[PLANIFICATEUR] Analyse automatique active — toutes les heures")
    print(f"[PLANIFICATEUR] Appuie sur Ctrl+C pour arrêter\n")

    # Boucle principale
    while True:
        schedule.run_pending()
        time.sleep(60)  # Vérifie toutes les minutes