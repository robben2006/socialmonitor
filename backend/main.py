"""
ÉTAPE 5 — Serveur API (FastAPI)
Fichier : backend/main.py

Ce fichier est le point d'entrée de l'application.
Il expose les données en JSON pour le tableau de bord.

Pour démarrer :
    uvicorn backend.main:app --reload --port 8000

Puis ouvre : http://localhost:8000/docs
(documentation interactive automatique !)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import sqlite3
import sys
import os

# Ajouter le dossier parent au path Python
sys.path.insert(0, os.path.dirname(__file__))

from models import (
    init_database, get_stats_summary, get_connection,
    insert_post, get_unanalyzed_posts
)

# ─────────────────────────────────────────────
#  CRÉATION DE L'APPLICATION FASTAPI
# ─────────────────────────────────────────────

app = FastAPI(
    title="SocialMonitor API",
    description="API d'analyse des réseaux sociaux pour l'institution académique",
    version="1.0.0",
)

# Autoriser le dashboard (React) à appeler cette API
# En production, remplace "*" par l'URL de ton frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
#  ÉVÉNEMENT DE DÉMARRAGE
# ─────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialise la base de données au démarrage du serveur."""
    init_database()
    print("[API] Serveur démarré ✓")
    print("[API] Documentation : http://localhost:8000/docs")


# ─────────────────────────────────────────────
#  ROUTES DE L'API
# ─────────────────────────────────────────────

@app.get("/")
def root():
    """Route racine — vérifie que le serveur tourne."""
    return {
        "status": "ok",
        "message": "SocialMonitor API en ligne",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api/dashboard")
def get_dashboard():
    """
    Retourne toutes les données pour le tableau de bord principal.
    C'est la route principale appelée par le frontend React.
    """
    try:
        data = get_stats_summary()

        # Reformater pour le frontend
        stats = data["stats"]
        total = stats["total"] or 1  # Éviter la division par zéro

        return {
            "summary": {
                "total_posts": stats["total"] or 0,
                "positive": stats["positive"] or 0,
                "negative": stats["negative"] or 0,
                "neutral": stats["neutral"] or 0,
                "positive_pct": round((stats["positive"] or 0) / total * 100, 1),
                "negative_pct": round((stats["negative"] or 0) / total * 100, 1),
                "alert_count": len(data["alerts"]),
                "top_subject": data["subjects"][0]["subject"] if data["subjects"] else "N/A",
            },
            "subjects": [
                {
                    "name": s["subject"],
                    "count": s["count"],
                    "sentiment": round(s["avg_score"] or 0, 3),
                }
                for s in data["subjects"]
            ],
            "alerts": [
                {
                    "id": a["id"],
                    "subject": a["subject"],
                    "text": a["message"],
                    "severity": a["severity"],
                    "count": a["count"],
                    "time": a["created_at"],
                }
                for a in data["alerts"]
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/posts")
def get_posts(limit: int = 20, sentiment: str = None, subject: str = None):
    """
    Retourne les derniers posts analysés.
    
    Paramètres optionnels :
      - limit   : nombre de posts (défaut 20)
      - sentiment : 'positif', 'negatif', 'neutre'
      - subject : filtrer par sujet
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM posts WHERE is_analyzed = 1"
    params = []

    if sentiment:
        query += " AND sentiment_label = ?"
        params.append(sentiment)

    if subject:
        query += " AND subject = ?"
        params.append(subject)

    query += " ORDER BY collected_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {"posts": posts, "count": len(posts)}


@app.get("/api/timeline")
def get_timeline():
    """
    Retourne l'évolution du sentiment heure par heure (dernières 24h).
    Utilisé pour le graphique du tableau de bord.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            strftime('%H', collected_at) as hour,
            SUM(CASE WHEN sentiment_label = 'positif' THEN 1 ELSE 0 END) as positive,
            SUM(CASE WHEN sentiment_label = 'negatif' THEN 1 ELSE 0 END) as negative,
            SUM(CASE WHEN sentiment_label = 'neutre'  THEN 1 ELSE 0 END) as neutral
        FROM posts
        WHERE is_analyzed = 1
          AND collected_at >= datetime('now', '-24 hours')
        GROUP BY hour
        ORDER BY hour
    """)

    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {"timeline": rows}


@app.post("/api/posts/add")
def add_post_manually(data: dict):
    """
    Ajoute un post manuellement (utile pour les tests).
    
    Corps de la requête (JSON) :
        { "content": "Texte du post", "author": "Nom optionnel" }
    """
    content = data.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Le champ 'content' est requis")

    post_id = insert_post(
        source="manual",
        content=content,
        author=data.get("author", "Anonyme")
    )

    if post_id is None:
        raise HTTPException(status_code=409, detail="Post déjà existant")

    # Analyser immédiatement ce post
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nlp'))
        from nlp.analyzer import classify_subject, analyze_sentiment
        from models import update_post_analysis

        subject = classify_subject(content)
        label, score = analyze_sentiment(content)
        update_post_analysis(post_id, subject, label, score)

        return {
            "status": "ok",
            "post_id": post_id,
            "analysis": {
                "subject": subject,
                "sentiment": label,
                "score": score,
            }
        }
    except Exception as e:
        return {"status": "ok", "post_id": post_id, "warning": str(e)}


@app.post("/api/analyze")
def trigger_analysis():
    """
    Déclenche manuellement l'analyse NLP sur tous les posts non traités.
    En production, cela se fait automatiquement toutes les heures.
    """
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from nlp.analyzer import run_analysis_pipeline
        run_analysis_pipeline()
        return {"status": "ok", "message": "Analyse terminée"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/collect")
def trigger_collection():
    """
    Déclenche manuellement la collecte de données depuis toutes les sources.
    """
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from collectors.collector import run_all_collectors
        count = run_all_collectors(use_manual=True)
        return {"status": "ok", "new_posts": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/alerts")
def get_alerts(unread_only: bool = True):
    """Retourne les alertes actives."""
    conn = get_connection()
    cursor = conn.cursor()

    if unread_only:
        cursor.execute("SELECT * FROM alerts WHERE is_read = 0 ORDER BY created_at DESC")
    else:
        cursor.execute("SELECT * FROM alerts ORDER BY created_at DESC LIMIT 50")

    alerts = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"alerts": alerts}


@app.post("/api/alerts/{alert_id}/read")
def mark_alert_read(alert_id: int):
    """Marque une alerte comme lue."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE alerts SET is_read = 1 WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}