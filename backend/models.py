"""
ÉTAPE 2 — Base de données
Fichier : backend/models.py

Ce fichier définit les tables de la base de données.
On utilise SQLite (aucune installation serveur nécessaire).
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = "socialmonitor.db"


def get_connection():
    """Retourne une connexion à la base de données."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par nom
    return conn


def init_database():
    """
    Crée les tables si elles n'existent pas encore.
    À appeler une seule fois au démarrage de l'application.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # --- Table principale : chaque post/commentaire collecté ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source          TEXT NOT NULL,        -- 'facebook', 'twitter', 'manual'
            external_id     TEXT UNIQUE,          -- ID du post sur la plateforme source
            content         TEXT NOT NULL,        -- Texte du post
            author          TEXT,                 -- Auteur (anonymisé si besoin)
            posted_at       TEXT,                 -- Date de publication (ISO 8601)
            collected_at    TEXT NOT NULL,        -- Date de collecte par notre outil
            
            -- Résultats de l'analyse NLP (remplis après traitement)
            subject         TEXT,                 -- ex: 'Infrastructure', 'Examens'
            sentiment_label TEXT,                 -- 'positif', 'negatif', 'neutre'
            sentiment_score REAL,                 -- Score entre -1.0 et +1.0
            is_analyzed     INTEGER DEFAULT 0     -- 0 = pas encore analysé, 1 = fait
        )
    """)

    # --- Table des alertes générées automatiquement ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            subject     TEXT NOT NULL,
            message     TEXT NOT NULL,
            severity    TEXT NOT NULL,            -- 'high', 'medium', 'low'
            count       INTEGER NOT NULL,         -- Nombre de posts concernés
            created_at  TEXT NOT NULL,
            is_read     INTEGER DEFAULT 0         -- 0 = non lue, 1 = lue
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Base de données initialisée ✓")


def insert_post(source, content, external_id=None, author=None, posted_at=None):
    """
    Insère un nouveau post dans la base.
    Retourne l'ID inséré, ou None si le post existe déjà (external_id en double).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO posts (source, external_id, content, author, posted_at, collected_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            source,
            external_id,
            content,
            author,
            posted_at,
            datetime.now().isoformat()
        ))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        # external_id déjà présent → post déjà collecté, on l'ignore
        return None
    finally:
        conn.close()


def get_unanalyzed_posts():
    """Retourne tous les posts qui n'ont pas encore été analysés."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts WHERE is_analyzed = 0")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def update_post_analysis(post_id, subject, sentiment_label, sentiment_score):
    """Met à jour un post avec les résultats de l'analyse NLP."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE posts
        SET subject = ?, sentiment_label = ?, sentiment_score = ?, is_analyzed = 1
        WHERE id = ?
    """, (subject, sentiment_label, sentiment_score, post_id))
    conn.commit()
    conn.close()


def insert_alert(subject, message, severity, count):
    """Insère une nouvelle alerte."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alerts (subject, message, severity, count, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (subject, message, severity, count, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_stats_summary():
    """
    Retourne les statistiques globales pour le tableau de bord.
    C'est la requête principale qu'utilise l'API.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN sentiment_label = 'positif' THEN 1 ELSE 0 END) as positive,
            SUM(CASE WHEN sentiment_label = 'negatif' THEN 1 ELSE 0 END) as negative,
            SUM(CASE WHEN sentiment_label = 'neutre'  THEN 1 ELSE 0 END) as neutral
        FROM posts WHERE is_analyzed = 1
    """)
    stats = dict(cursor.fetchone())

    cursor.execute("""
        SELECT subject, COUNT(*) as count, AVG(sentiment_score) as avg_score
        FROM posts WHERE is_analyzed = 1
        GROUP BY subject ORDER BY count DESC LIMIT 5
    """)
    subjects = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT * FROM alerts WHERE is_read = 0 ORDER BY created_at DESC LIMIT 10
    """)
    alerts = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {"stats": stats, "subjects": subjects, "alerts": alerts}


# --- Test rapide ---
if __name__ == "__main__":
    init_database()
    # Insérer un post de test
    post_id = insert_post(
        source="manual",
        content="La connexion Wi-Fi à la bibliothèque est catastrophique aujourd'hui",
        author="Étudiant anonyme"
    )
    print(f"[TEST] Post inséré avec l'ID : {post_id}")
    print(f"[TEST] Posts non analysés : {len(get_unanalyzed_posts())}")