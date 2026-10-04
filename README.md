# Distributed File Sharing System (DCC)

A full-stack, distributed file-sharing application designed with a React frontend, a FastAPI backend master server, multiple independent storage nodes, and PostgreSQL for metadata storage.

## Prerequisites

Before running the project, make sure you have the following installed on your system:
- **Docker Desktop** (Make sure the Docker daemon is fully started and running)
- Note: There's no need to install Node/Python on your host machine because everything runs inside Docker containers.

## 🚀 How to Run the Project (Using Docker)

The entire architecture is containerized and orchestrated with Docker Compose. This starts the PostgreSQL database, the Master Backend, the Vite Frontend server, and 3 distinct storage nodes.

### 1. Build and Start the Application
Open a terminal in the root directory (where `docker-compose.yml` is located) and run:

```bash
docker-compose up --build
```
*(If you wish to run the containers in the background, you can use `docker-compose up -d --build`)*

Let the terminal process run. The first build may take a few minutes as it downloads base images and installs dependencies.

### 2. Access the Application

Once everything is up and running, you can interact with the system via your browser:

- **Frontend Dashboard:** [http://localhost:5173](http://localhost:5173) 
  *(This is where users interact with the app, manage, and share files).*
- **Backend API Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
  *(Full interactive API documentation).*

### 3. Default Login Credentials
You can log in to the frontend immediately using the pre-seeded System Admin account:
- **Email:** `admin@dfs.local`
- **Password:** `Admin@123`
*(You can also use the UI to register your own accounts).*

## 🔌 Architecture URLs
If you need to verify the health of the individual moving parts:
- **Storage Node 1:** http://localhost:8001/health
- **Storage Node 2:** http://localhost:8002/health
- **Storage Node 3:** http://localhost:8003/health
- **Postgres Database:** Exposed on `localhost:5432`

## 🛑 How to Stop the Project

If you ran it in the foreground (without `-d`), simply hit **Ctrl+C** in your terminal.

To cleanly shut down and completely remove the containers, run:
```bash
docker-compose down
```

*(Note: Data volumes will persist so your uploaded files and database aren't wiped when restarting. To completely reset all data, use `docker-compose down -v`).*
