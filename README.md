![semver](https://img.shields.io/badge/semver-0.1.0-blue)

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-360/)
[![poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)


[![CI](https://github.com/spackle0/status-tiles/actions/workflows/docker-build-test.yaml/badge.svg)](https://github.com/johndoe/my-project/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/spackle0/status-tiles/graph/badge.svg?token=YJVD7W9Q37)](https://codecov.io/gh/spackle0/status-tiles)

[![Snyk Security](https://snyk.io/test/github/spackle0/status-tiles/badge.svg)](https://snyk.io/test/github/spackle0/status-tiles)
[![Dependencies Status](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen.svg)](https://github.com/spackle0/status-tiles/pulls?utf8=%E2%9C%93&q=is%3Apr%20author%3Aapp%2Fdependabot)


# Status Tiles
Experiment in consolidating status notifications from third parties.

## Challenge
In my work in infrastructure I often have to keep track of the status of many
third party serivces. This can be especially painful in an outage situation
where I much to check multiple dashboards to get a full picture of what may be
happening.

## Solution
This project is an experiment to consolidate multiple dashboards into a single
page that can be easily checked.

This is also to exercise my skills in FastAPI and teach myself htmx.

## Running

Using [go-task](https://taskfile.dev/) you can run the following commands:

`task`: Show all the tasks available via the Taskfile.yaml

* `task compose:dev`             Start Docker Compose services in development mode
* `task compose:down`            Stop Docker Compose services
* `task compose:logs`            View Docker Compose logs
* `task compose:up`              Start Docker Compose services
* `task docker:build`            Build the production Docker image for running the application
* `task docker:build-test`       Build the testing Docker image for unit testing
* `task docker:run`              Run Docker container
* `task docker:test`             Run unit tests inside the testing Docker container

Once the container is running, you can view the application at http://localhost:8000

## Configuring

* Copy `.env.example` to `.env` and edit any values as needed

* `config.yaml` lists the services to be checked. For example:

```yaml
services:
  - name: "GitHub Status"
    type: "rss"
    config:
      name: "GitHub"
      feed_url: "https://www.githubstatus.com/history.rss"
      timeout: 30
    polling_interval: 300
```

At the moment, only RSS is supported
