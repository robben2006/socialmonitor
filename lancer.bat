@echo off
title SocialMonitor — Lancement
color 0B
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║         SocialMonitor — Démarrage            ║
echo  ║     Lancement de tous les services...        ║
echo  ╚══════════════════════════════════════════════╝
echo.

cd /d C:\Users\user\socialmonitor

echo  [1/3] Démarrage du serveur API...
start "SocialMonitor — API" cmd /k "cd /d C:\Users\user\socialmonitor && python -m uvicorn backend.main:app --reload --port 8000"

echo  Attente de 3 secondes...
timeout /t 3 /nobreak > nul

echo  [2/3] Démarrage du planificateur...
start "SocialMonitor — Planificateur" cmd /k "cd /d C:\Users\user\socialmonitor && python backend/scheduler.py"

echo  Attente de 3 secondes...
timeout /t 3 /nobreak > nul

echo  [3/3] Démarrage du tableau de bord...
start "SocialMonitor — Dashboard" cmd /k "cd /d C:\Users\user\socialmonitor\dashboard && npm start"

echo.
echo  ✓ Tous les services sont en cours de démarrage !
echo.
echo  Le navigateur va s'ouvrir automatiquement sur :
echo  http://localhost:3000
echo.
echo  Pour tout arrêter : ferme les 3 fenêtres noires.
echo.
pause
