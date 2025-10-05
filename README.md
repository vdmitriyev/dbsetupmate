## About

The project takes on the role of a database mate, whose purpose is to create and maintain database schemas inside a single database instance.

## Deployment: Docker Compose

On server files are located in directory: `/opt/dbmate/`

* (linux) create directories to store data and provide correct access rights:
    ```
	mkdir /opt/dbmate/
	cd /opt/dbmate/
    sudo mkdir .configs
    sudo mkdir .logs
    sudo chown -R $USER:$USER /opt/dbmate/
    ```
* Using docker compose
	```
	docker compose up
	```
* Using docker compose (detach mode)
	```
	docker compose up -d
	```
* (optional) Rebuild ```dbmate``` on demand
	```bash
	docker compose up -d --no-deps --build app
	```

## License

[MIT](LICENSE)