# Payment And Order Service

Сервис реализует работу с платежами по заказу:
- типы платежа: `cash`, `acquiring`;
- операции: создание платежа (`deposit`) и возврат (`refund`);
- сумма активных платежей (`pending + success`) не превышает сумму заказа;
- статус заказа пересчитывается централизованно (`not_paid`, `partially_paid`, `paid`);
- для acquiring есть синхронизация состояния с банком.

## Технологии
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Loguru
- Docker Compose

## Запуск

1. Создать `.env` по примеру `.env.example`.
2. Запустить сервисы:

```bash
docker compose up --build -d
```

3. Проверить, что миграции применились и сервис поднят:

```bash
docker compose logs -f app
```

Приложение будет доступно на `http://localhost:8000`.

## Миграции Alembic

При старте контейнера `app` выполняется:

```bash
alembic upgrade head
```

Это создает схему БД и стартовые заказы из первой миграции.

Ручной запуск миграций:

```bash
docker compose exec app alembic upgrade head
```

## Ручная проверка через Swagger

Swagger UI:
- `http://localhost:8000/docs`

Эндпоинты для проверки:
- `GET /orders/{order_id}`
- `POST /payments`
- `POST /payments/{payment_id}/refund`
- `GET /payments/{payment_id}`
- `POST /payments/sync`

## Тесты в Docker

Разовый запуск тестов:

```bash
docker compose run --rm app sh -lc "pytest -q"
```

Запуск тестов в уже поднятом контейнере:

```bash
docker compose exec app sh -lc "pytest -q"
```

## Логирование

Используется `loguru`:
- логи запуска/остановки приложения;
- логи входящих HTTP запросов;
- логи бизнес-операций и синхронизации с банком.

## Схема БД
- SQL: `schema.sql`
- диаграмма: `docs/db_schema.md`
