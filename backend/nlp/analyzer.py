"""
ÉTAPE 3 (améliorée) — Cerveau analytique NLP avec CamemBERT
Fichier : backend/nlp/analyzer.py

Remplace VADER par CamemBERT — modèle 100% français,
bien plus précis sur les textes académiques et étudiants.

Modèle utilisé : tblard/tf-allocine
  - Entraîné sur des critiques françaises
  - Fonctionne très bien sur les textes courts
  - Tourne sur CPU (pas besoin de GPU)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from transformers import pipeline
from models import get_unanalyzed_posts, update_post_analysis, insert_alert, get_connection

print("[NLP] Chargement du modèle CamemBERT... (première fois : ~30 secondes)")

# ─────────────────────────────────────────────
#  CHARGEMENT DU MODÈLE
#  La première fois, télécharge ~250MB
#  Les fois suivantes, utilise le cache local
# ─────────────────────────────────────────────
try:
    sentiment_model = pipeline(
        "text-classification",
        model="cardiffnlp/twitter-xlm-roberta-base-sentiment",
tokenizer="cardiffnlp/twitter-xlm-roberta-base-sentiment",
        top_k=None,   # Retourne les scores pour toutes les classes
    )
    print("[NLP] Modèle CamemBERT chargé ✓")
    USE_CAMEMBERT = True
except Exception as e:
    print(f"[NLP] CamemBERT indisponible ({e}), repli sur VADER")
    USE_CAMEMBERT = False
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()


# ─────────────────────────────────────────────
#  DICTIONNAIRE DES SUJETS (inchangé)
# ─────────────────────────────────────────────
SUBJECT_KEYWORDS = {
    "Infrastructure & Wi-Fi": [
        "wifi", "wi-fi", "connexion", "internet", "réseau", "débit",
        "bibliothèque", "labo", "laboratoire", "salle informatique",
        "ordinateur", "projecteur", "climatisation", "chauffage", "panne",
    ],
    "Examens & Évaluations": [
        "examen", "exam", "partiel", "résultat", "note", "notation",
        "correction", "rattrapage", "contrôle", "ds", "concours",
        "épreuve", "qcm", "devoir", "partials",
    ],
    "Administration": [
        "inscription", "scolarité", "secrétariat", "dossier", "bourse",
        "attestation", "certificat", "administration", "directeur",
        "service", "délai", "réponse", "traitement",
    ],
    "Vie Étudiante": [
        "soirée", "foyer", "cafétéria", "cantine", "repas", "restaurant",
        "association", "club", "sport", "gymnase", "fête", "événement",
        "sortie", "voyage", "logement", "résidence", "intégration",
    ],
    "Cours & Pédagogie": [
        "cours", "prof", "professeur", "enseignant", "programme",
        "planning", "emploi du temps", "amphi", "td", "tp",
        "module", "matière", "filière", "cursus", "formation",
    ],
}
DEFAULT_SUBJECT = "Général"


# ─────────────────────────────────────────────
#  1. ANALYSE DE SENTIMENT (CamemBERT)
# ─────────────────────────────────────────────

def analyze_sentiment(text: str) -> tuple:
    """
    Analyse le sentiment d'un texte avec CamemBERT.

    Retourne :
        label : 'positif', 'negatif', ou 'neutre'
        score : float entre -1.0 (très négatif) et +1.0 (très positif)

    Exemples :
        >>> analyze_sentiment("La connexion Wi-Fi est catastrophique !")
        ('negatif', -0.94)

        >>> analyze_sentiment("Super ambiance aujourd'hui !")
        ('positif', 0.97)
    """
    if not text or not text.strip():
        return "neutre", 0.0

    # Tronquer à 512 tokens max (limite du modèle)
    text_truncated = text[:512]

    if USE_CAMEMBERT:
        try:
            results = sentiment_model(text_truncated)[0]

            # Extraire les scores positif et négatif
            scores = {r["label"].upper(): r["score"] for r in results}
            pos_score = scores.get("POSITIVE", scores.get("POS", 0.5))
            neg_score = scores.get("NEGATIVE", scores.get("NEG", 0.5))

            # Convertir en score entre -1 et +1
            compound = pos_score - neg_score

            # Seuils de classification
            if compound >= 0.15:
                label = "positif"
            elif compound <= -0.15:
                label = "negatif"
            else:
                label = "neutre"

            return label, round(compound, 3)

        except Exception as e:
            print(f"[NLP] Erreur CamemBERT sur '{text[:40]}...' : {e}")
            return "neutre", 0.0
    else:
        # Repli sur VADER si CamemBERT échoue
        scores = _vader.polarity_scores(text.lower())
        compound = scores["compound"]
        if compound >= 0.05:
            label = "positif"
        elif compound <= -0.05:
            label = "negatif"
        else:
            label = "neutre"
        return label, round(compound, 3)


# ─────────────────────────────────────────────
#  2. CLASSIFICATION DU SUJET (inchangée)
# ─────────────────────────────────────────────

def classify_subject(text: str) -> str:
    """Détermine le sujet d'un post par correspondance de mots-clés."""
    text_lower = text.lower()
    scores = {}
    for subject, keywords in SUBJECT_KEYWORDS.items():
        match_count = sum(1 for kw in keywords if kw in text_lower)
        if match_count > 0:
            scores[subject] = match_count
    if not scores:
        return DEFAULT_SUBJECT
    return max(scores, key=scores.get)


# ─────────────────────────────────────────────
#  3. MOTEUR D'ALERTES (inchangé)
# ─────────────────────────────────────────────

ALERT_THRESHOLD = 5


def check_and_generate_alerts():
    """Génère des alertes si un sujet accumule trop de posts négatifs."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT subject, COUNT(*) as neg_count
        FROM posts
        WHERE sentiment_label = 'negatif'
          AND is_analyzed = 1
          AND collected_at >= datetime('now', '-24 hours')
        GROUP BY subject
        HAVING neg_count >= ?
        ORDER BY neg_count DESC
    """, (ALERT_THRESHOLD,))
    problem_subjects = cursor.fetchall()
    conn.close()

    for row in problem_subjects:
        subject = row[0]
        neg_count = row[1]
        severity = "high" if neg_count >= 20 else "medium" if neg_count >= 10 else "low"
        message = (
            f"Pic de {neg_count} commentaires négatifs détecté "
            f"sur le sujet « {subject} » dans les dernières 24h."
        )
        insert_alert(subject, message, severity, neg_count)
        print(f"[ALERTE] {severity.upper()} — {message}")


# ─────────────────────────────────────────────
#  4. PIPELINE PRINCIPAL
# ─────────────────────────────────────────────

def run_analysis_pipeline():
    """Lance l'analyse complète sur tous les posts non traités."""
    posts = get_unanalyzed_posts()
    print(f"[NLP] {len(posts)} posts à analyser avec CamemBERT...")

    for post in posts:
        text = post["content"]
        subject = classify_subject(text)
        sentiment_label, sentiment_score = analyze_sentiment(text)
        update_post_analysis(
            post_id=post["id"],
            subject=subject,
            sentiment_label=sentiment_label,
            sentiment_score=sentiment_score
        )
        print(f"  ✓ [{sentiment_label:8s} | {sentiment_score:+.3f}] [{subject}] {text[:55]}...")

    check_and_generate_alerts()
    print(f"[NLP] Pipeline CamemBERT terminé ✓")


# ─────────────────────────────────────────────
#  TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        "La connexion Wi-Fi à la bibliothèque est catastrophique aujourd'hui",
        "Super ambiance pendant la semaine des examens, bonne chance à tous !",
        "Les résultats du partiel ne sont toujours pas en ligne...",
        "Le prof de Mathématiques manque trop les cours",
        "Aucune réponse du secrétariat depuis 2 semaines pour mon dossier",
        "Soirée étudiante vendredi, c'est validé !!",
        "Le secrétariat ne répond jamais, c'est vraiment décevant",
        "Excellent cours de mathématiques ce matin, merci professeur !",
    ]
    print("\n" + "=" * 65)
    print("TEST DU MOTEUR NLP — CamemBERT")
    print("=" * 65)
    for text in tests:
        subject = classify_subject(text)
        label, score = analyze_sentiment(text)
        emoji = "✅" if label == "positif" else "❌" if label == "negatif" else "➖"
        print(f"\n{emoji} Texte    : {text}")
        print(f"   Sujet    : {subject}")
        print(f"   Sentiment: {label} (score: {score:+.3f})")
    print("\n" + "=" * 65)