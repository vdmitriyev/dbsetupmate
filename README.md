## About

`dbmate` is a Python package and CLI, which overtakes a role of a database mate. Primary purpose is to create and maintain database schemas and users.

## Install

Installation using `uv`

```
uv pip install dbmate
```

Copy `sample.env` to `.env` and adjust the `POSTGRESQL_*` values.

## CLI Mode

* Show the available commands and options
  ```
  dbmate --help
  ```
* Create a database together with its owner and login user
  ```
  dbmate --env-file .env db create-db --new-db-name course_db_01 --new-db-user course_user_01
  ```
* Next free generated database name
  ```
  dbmate --env-file .env db show-next-db-name
  ```
* Create the shared database
  ```
  dbmate --env-file .env db create-shared-db
  ```
* Read-only user for the shared database
  ```
  dbmate --env-file .env db create-user-readonly
  ```
* Grant an existing user read-only access to the shared database
  ```
  dbmate --env-file .env db grant-shared-access --user-name course_user_01
  ```
* There is also a `dry-run` option for all commands
  ```
    dbmate --env-file .env --dry-run db create-db
    ```

P.S. The password is prompted for when `--new-db-password` is omitted. Commands exit `1` on failure.

## Library Mode

Here is a example how to use `dbmate` as Python library.

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

## Development: Setup

This guide walks through setting up the project for local development using `uv`.

1. Create a new virtual environment in a `.venv` directory and activates it.
    ```bash
    uv venv
    ```
1. Activate the environment (macOS/Linux):
   ```
   source .venv/bin/activate
   ```
1. Activate the environment (Windows):
    ```
    call .venv/Scripts/activate.bat
    ```
1.  Install package in **editable mode** with **dev** dependencies
    Installing the package in **editable mode** (`-e`) is the key to development.
    ```bash
    uv pip install -e . --group dev
    ```

## Development: Running Tests

```bash
task py:pytest              # unit tests, no database needed
task py:pytest-integration  # against live PostgreSQL 15..18 (see compose-tests.yaml)
```

## License

[MIT](LICENSE)
