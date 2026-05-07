"""
ÉTAPE 4 — Collecteur de données (Connecteur)
Fichier : backend/collectors/collector.py

Ce fichier contient les fonctions pour récupérer
les posts depuis différentes sources :
  - Facebook (via l'API Graph officielle)
  - Twitter/X (via l'API v2)
  - Source manuelle (pour tester sans API)

IMPORTANT : Pour utiliser Facebook ou Twitter,
tu dois créer une application développeur (expliqué
dans le guide README.md ci-dessous).
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()


# Importer la base de données
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models import insert_post


# ─────────────────────────────────────────────
#  SOURCE 1 : DONNÉES MANUELLES (aucune API)
#  Parfait pour tester sans configuration
# ─────────────────────────────────────────────

SAMPLE_POSTS = [
    "La connexion Wi-Fi à la bibliothèque est catastrophique aujourd'hui",
    "Super ambiance pendant la semaine des examens, bonne chance à tous !",
    "Les résultats du partiel ne sont toujours pas en ligne...",
    "Soirée étudiante vendredi, c'est validé !!",
    "Le secrétariat ne répond jamais, c'est vraiment décevant",
    "Nouveau projet en groupe pour le module IA, l'équipe est motivée !",
    "Impossible de s'inscrire au rattrapage, le site plante en boucle",
    "Le prof de maths est vraiment excellent, ses explications sont claires",
    "La cantine était fermée sans prévenir aujourd'hui, c'est scandaleux",
    "Merci à l'association étudiante pour l'organisation du tournoi de foot !",
    "L'amphi A est trop petit pour notre promotion, c'est inconfortable",
    "Les notes du devoir surveillé ont été rendues rapidement, bravo !",
    "Le chauffage dans les salles de cours ne fonctionne toujours pas",
    "Super journée d'intégration pour les nouveaux étudiants !",
    "Aucune réponse du secrétariat depuis 2 semaines pour mon dossier",
]


def collect_manual_posts():
    """
    Insère les posts d'exemple en base de données.
    Utilisé pour tester l'application sans connexion aux réseaux sociaux.
    """
    print("[COLLECTEUR] Chargement des posts manuels...")
    count = 0
    for i, text in enumerate(SAMPLE_POSTS):
        post_id = insert_post(
            source="manual",
            content=text,
            external_id=f"manual_{i}",
            author="Étudiant anonyme"
        )
        if post_id:  # None = doublon, déjà en base
            count += 1

    print(f"[COLLECTEUR] {count} nouveaux posts ajoutés ✓")
    return count


# ─────────────────────────────────────────────
#  SOURCE 2 : FACEBOOK (API Graph officielle)
#
#  Prérequis :
#  1. Créer une app sur developers.facebook.com
#  2. Obtenir un "Page Access Token"
#  3. Remplir FACEBOOK_ACCESS_TOKEN et FACEBOOK_PAGE_ID dans .env
# ─────────────────────────────────────────────

def collect_facebook_posts():
    """
    Récupère les derniers posts et commentaires d'une Page Facebook.
    
    COMMENT OBTENIR TON TOKEN FACEBOOK :
    ─────────────────────────────────────
    1. Va sur https://developers.facebook.com
    2. Crée une application (type : "Business")
    3. Ajoute le produit "Facebook Login"
    4. Dans "Graph API Explorer", sélectionne ta page
    5. Génère un token avec les permissions :
       - pages_read_engagement
       - pages_read_user_content
    6. Copie le token dans ton fichier .env
    """
    token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID")

    if not token or not page_id:
        print("[FACEBOOK] ⚠️  Variables manquantes dans .env (FACEBOOK_ACCESS_TOKEN, FACEBOOK_PAGE_ID)")
        print("[FACEBOOK]    → Consulte le README pour la configuration")
        return 0

    count = 0
    url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
    params = {
        "access_token": token,
        "fields": "id,message,created_time,from",
        "limit": 50,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        for post in data.get("data", []):
            message = post.get("message", "")
            if not message:
                continue  # Ignorer les posts sans texte

            post_id = insert_post(
                source="facebook",
                content=message,
                external_id=post.get("id"),
                author=post.get("from", {}).get("name", "Anonyme"),
                posted_at=post.get("created_time")
            )
            if post_id:
                count += 1

        print(f"[FACEBOOK] {count} nouveaux posts collectés ✓")

    except requests.exceptions.RequestException as e:
        print(f"[FACEBOOK] Erreur de connexion : {e}")

    return count


# ─────────────────────────────────────────────
#  SOURCE 3 : TWITTER / X (API v2)
#
#  Prérequis :
#  1. Créer un compte développeur sur developer.twitter.com
#  2. Créer un projet et une application
#  3. Obtenir le "Bearer Token"
#  4. Remplir TWITTER_BEARER_TOKEN dans .env
# ─────────────────────────────────────────────

def collect_twitter_posts():
    """
    Récupère les tweets récents correspondant aux mots-clés de l'école.
    
    COMMENT OBTENIR TON BEARER TOKEN TWITTER :
    ───────────────────────────────────────────
    1. Va sur https://developer.twitter.com
    2. Crée un "Project" puis une "App"
    3. Dans "Keys and tokens", copie le "Bearer Token"
    4. Colle-le dans .env sous TWITTER_BEARER_TOKEN
    
    ⚠️  Note : L'API gratuite de Twitter est limitée à 500 000 tweets/mois
    """
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    keywords = os.getenv("TWITTER_KEYWORDS", "#MonEcole")

    if not bearer_token:
        print("[TWITTER] ⚠️  TWITTER_BEARER_TOKEN manquant dans .env")
        return 0

    count = 0
    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {bearer_token}"}
    params = {
        "query": f"{keywords} lang:fr -is:retweet",
        "tweet.fields": "created_at,author_id,text",
        "max_results": 100,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        for tweet in data.get("data", []):
            post_id = insert_post(
                source="twitter",
                content=tweet["text"],
                external_id=tweet["id"],
                author=tweet.get("author_id"),
                posted_at=tweet.get("created_at")
            )
            if post_id:
                count += 1

        print(f"[TWITTER] {count} nouveaux tweets collectés ✓")

    except requests.exceptions.RequestException as e:
        print(f"[TWITTER] Erreur de connexion : {e}")

    return count


# ─────────────────────────────────────────────
#  COLLECTEUR PRINCIPAL — appelle toutes les sources
# ─────────────────────────────────────────────

def run_all_collectors(use_manual=True):
    """
    Lance tous les collecteurs configurés.
    
    Args:
        use_manual: Si True, charge aussi les posts d'exemple (pour les tests)
    """
    print("\n" + "=" * 50)
    print("DÉMARRAGE DE LA COLLECTE")
    print("=" * 50)

    total = 0

    if use_manual:
        total += collect_manual_posts()

    total += collect_facebook_posts()
    total += collect_twitter_posts()

    print(f"\n[COLLECTEUR] Total : {total} nouveaux posts collectés")
    return total


# --- Test rapide ---
if __name__ == "__main__":
    # Initialiser la base d'abord
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from models import init_database
    init_database()

    # Lancer la collecte avec les données manuelles uniquement
    run_all_collectors(use_manual=True)