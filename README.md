# cortexm-highlights
Plateforme Django de generation automatique de highlights football.

## Stack
- Django + DRF + Templates + HTMX
- PostgreSQL
- Celery + Redis
- Django Channels (WebSocket)
- FFmpeg + OpenCV (pipeline modulaire)
- Stockage configurable (local, S3, Azure Blob)

## Features principales
- Upload video (mp4/mov) -> creation d'un Project
- Lancement d'un ProcessingJob asynchrone avec duree cible (5/7/10 minutes)
- Progression temps reel (WebSocket) avec etapes: ingestion, segmentation, event_detection, selection, render
- Previsualisation des segments selectionnes (timecodes + thumbnails)
- Rendu final MP4 + telechargement
- Gestion d'erreurs + retries Celery + EventLog

## Structure
```
cortexm_highlights/    Django project (settings, ASGI/WSGI, Celery)
highlights/            App principale (models, views, templates, consumers)
services/video_pipeline/
  ffmpeg.py            Helpers ffmpeg/ffprobe
  transcode.py         Proxy video
  segmentation.py      Shot segmentation basique
  scoring.py           Motion scoring + placeholder audio peaks
  selection.py         Selection segments cible
  thumbnails.py        Extractions images
  render.py            Concat final
```

## Setup local (Docker)
1. Copier les variables:
   - `cp .env.example .env`
2. Demarrer:
   - `docker-compose up --build`
3. Migrer:
   - `docker-compose exec web python manage.py migrate`
4. (Optionnel) Superuser:
   - `docker-compose exec web python manage.py createsuperuser`
5. Acces:
   - App: http://localhost:8000
   - Admin: http://localhost:8000/admin

## Setup local (sans Docker)
1. Installer FFmpeg.
2. Creer un venv et installer les deps:
   - `python -m venv .venv`
   - `.\.venv\Scripts\activate`
   - `pip install -r requirements.txt`
3. Configurer `.env` (voir `.env.example`).
4. Lancer PostgreSQL + Redis.
5. Migrer:
   - `python manage.py migrate`
6. Lancer le serveur:
   - `python manage.py runserver`
7. Lancer Celery:
   - `celery -A cortexm_highlights worker -l info`

## Variables d'environnement
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
- `DATABASE_URL`
- `REDIS_URL`
- `STORAGE_BACKEND` (`local`, `s3`, `azure`)
- `MEDIA_URL`
- S3: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`, `AWS_S3_ENDPOINT_URL`
- Azure: `AZURE_ACCOUNT_NAME`, `AZURE_ACCOUNT_KEY`, `AZURE_CONTAINER`

## Tests
- `python manage.py test`

## Notes pipeline
- La segmentation est simple (fenetre fixe) pour bootstraper.
- Motion scoring: OpenCV via difference entre frames.
- Audio peaks: placeholder neutre, a remplacer par une extraction audio (ffmpeg astats ou autre).
- Chaque etape met a jour `ProcessingJob.progress` et `current_step`, logge un EventLog, et publie un event WebSocket.
