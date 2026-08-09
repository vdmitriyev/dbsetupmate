## About

`dbmate` is a Python package and CLI, which overtakes a role of a database mate. Primary purpose is to create and maintain database schemas and users.

## Install

```bash
uv pip install -e . --group dev
```

Copy `sample.env` to `.env` and adjust the `POSTGRESQL_*` values.

## CLI

```bash
dbmate --help
dbmate --env-file .env db create-db --new-db-name course_db_01 --new-db-user course_user_01
dbmate --env-file .env db show-next-db-name      # next free generated database name
dbmate --env-file .env db create-demo-db         # create the shared demo database
dbmate --env-file .env db create-user-readonly   # read-only user for the demo database
dbmate --env-file .env -d db create-db           # -d dry run, -v verbose
```

The password is prompted for when `--new-db-password` is omitted. Commands exit `1` on failure.

## Library

```python
from dbmate import PostgresMate, PostgreSQLConfig, DBMateException

mate = PostgresMate(PostgreSQLConfig(host="db.internal", admin_password="..."))

try:
    created = mate.create_db("course_db_01", "course_user_01", "s3cret")
except DBMateException as ex:
    print(ex)
```

`PostgreSQLConfig.from_env()` reads the `POSTGRESQL_*` variables instead. Failures raise a
subclass of `DBMateException`, never a `bool`.

## Tests

```bash
task py:pytest                                       # unit tests, no database needed
docker compose -f compose-tests.yaml up -d database-15
POSTGRESQL_DB_HOST_PORT=5415 pytest -m integration   # against a real server
```

## License

[MIT](LICENSE)
