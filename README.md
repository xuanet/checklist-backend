# Backend for Checklist application

This repo implements the server and database of the Checklist application. The server is implemented in Flask running on port 5000, and the database is sqlite. The database is persistent across the same instance of the server/docker container.

## Execution

Build the docker image
`docker build -t checklist-backend .`

Run container
`docker run -p 5000:5000 -v ${PWD}/data:/app/data checklist-backend`

