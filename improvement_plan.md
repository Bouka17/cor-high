# Plan d'Amélioration des Algorithmes de Détection d'Actions Sportives

## 1. Objectif
Améliorer la précision de la détection des faits de jeu (buts, corners, pénaltys, fautes, etc.) en passant d'une analyse purement sonore à une analyse combinée **Audio + Vidéo**. L'algorithme doit fonctionner même pour les vidéos d'entraînement (sans public/commentateur).

## 2. Architecture Technique
### A. VisionAnalyzer (Nouveau)
Un nouveau module `core/vision_analyzer.py` utilisant `ultralytics` (YOLOv8) et `OpenCV`.
- **Détection d'Objets** : Joueurs, Ballon, Arbitre, Buts.
- **Détection de Transitions** : Identifier les replays (ralentis) via la détection de "logo wipes" ou de changements brusques de rythme.
- **Analyse de Trajectoire** : Suivre le mouvement du ballon pour détecter les tirs au but et les occasions manquées.
- **Zonage** : Identifier les zones du terrain (surface de réparation, corners) pour contextualiser les actions.

### B. Scoring Engine (Amélioration)
Modification de `services/video_pipeline/scoring.py` ou intégration directe dans le pipeline pour combiner les scores :
- **Score Sonore** : Toujours utile pour les matchs TV (cris de foule).
- **Score de Mouvement** : Indique une intensité de jeu.
- **Score Évènementiel** : Poids fort pour les évènements détectés (But > Corner > Faute).

### C. Détection Spécifique des Évènements
1. **Buts** : Ballons entrant dans le filet + célébrations (groupement de joueurs).
2. **Ralentis** : Détection de transitions graphiques (logo qui passe) et analyse de l'aspect ratio/vitesse (Optical Flow plus lent).
3. **Corners** : Reconnaissance de la vue "angle de corner" et présence de joueurs groupés dans la surface.
4. **Pénaltys** : Détection du point de pénalty et duel 1v1 Gardien/Tireur.
5. **Graves Fautes** : Chutes de joueurs après contact rapide (collision vectorielle).

## 3. Étapes d'Implémentation
1. **Création de `core/vision_analyzer.py`** : Base YOLO v8 pour la détection.
2. **Mise à jour de `highlights/tasks.py`** : Intégrer l'analyse vidéo en complément de l'audio.
3. **Développement des heuristiques de détection** :
    - Détecteur de Replay (Logo Wipe).
    - Détecteur de tirs (Vitesse de balle vers le but).
    - Détecteur de corners/fautes.
4. **Tests sur Vidéos d'Entraînement** : Prioriser la détection de la balle et des mouvements rapides.

## 4. Livrables
- Code source enrichi.
- Configuration optimisée pour Celery.
- Documentation des nouveaux évènements détectés.
