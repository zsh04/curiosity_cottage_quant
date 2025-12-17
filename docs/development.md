# Developer Guide: Audit V2 Cleanup

## 1. Database Migrations (Alembic)

We have moved from manual SQL scripts to **Alembic** for managing the database schema.

### Commands

- **Check Status**: `alembic current`
- **Apply Changes**: `alembic upgrade head`
- **Create Migration**: `alembic revision --autogenerate -m "description_of_change"`
- **Rollback**: `alembic downgrade -1`

### Best Practices

- Always run `alembic check` in CI to ensure your models (`app/dal/models.py`) match the migration history.
- Do not modify `infra/db/init/*.sql` anymore; use Alembic.

## 2. Frontend Development (TypeScript)

All new components must be written in **TypeScript** (`.tsx`).

- **No JS/JSX**: Legacy components have been converted.
- **Strict Typing**: Avoid `any`. Define interfaces for props.

### Building

```bash
cd frontend
npm run build
```

## 3. Vector Database (Quantum Memory)

We use `pgvector` for RAG.

- **Model**: `MarketStateEmbedding` (1536 dims).
- **Service**: `app/services/memory.py` handles embedding and retrieval.
- **Prerequisites**: `OPENAI_API_KEY` must be set in `.env` for embedding generation.
