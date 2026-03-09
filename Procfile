# SkillOS — Railway/Render/Heroku Procfile
# FastAPI is now the default server (replaces stdlib http.server)

web: uvicorn skillos.api.fastapi_app:app --host 0.0.0.0 --port $PORT --workers 4 --loop uvloop --http httptools
worker: celery -A skillos.worker_celery worker --loglevel=info --queues=evaluation,awards,emails,analytics
beat: celery -A skillos.worker_celery beat --loglevel=info
