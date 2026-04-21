# Local Development

## Backend

```bash
cd backend
pip install -e .[dev]
uvicorn app.main:app --reload
```

Run migrations:

```bash
alembic upgrade head
```

Seed data:

```bash
python -m app.seed
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## Worker

```bash
cd backend
celery -A app.worker.celery_app worker --loglevel=INFO
```

## Documentation Discipline

Every implementation milestone should update relevant docs and be committed with a clear Git message.
