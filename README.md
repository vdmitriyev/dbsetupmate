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
dbmate --env-file .env db create --new-db-name course_db_01 --new-db-user course_user_01
dbmate --env-file .env db next-names             # next free generated names
dbmate --env-file .env db init-demo              # create the shared demo database
dbmate --env-file .env db create-readonly-user   # read-only user for the demo database
dbmate --env-file .env -d db create              # -d dry run, -v verbose
```

The password is prompted for when `--new-db-password` is omitted. Commands exit `1` on failure.

## Library

```python
from dbmate import PostgresMate, PostgreSQLConfig, DBMateException

mate = PostgresMate(PostgreSQLConfig(host="db.internal", admin_password="..."))

try:
    created = mate.create_database("course_db_01", "course_user_01", "s3cret")
except DBMateException as ex:
    print(ex)
```

`PostgreSQLConfig.from_env()` reads the `POSTGRESQL_*` variables instead. Failures raise a
subclass of `DBMateException` (`DatabaseAlreadyExistsException`, `DBConnectionException`,
`InvalidIdentifierException`, ...), never a `bool`.

## Tests

```bash
task py:pytest                                       # unit tests, no database needed
docker compose -f compose-tests.yaml up -d database-15
POSTGRESQL_DB_HOST_PORT=5415 pytest -m integration   # against a real server
```

## License

[MIT](LICENSE)
