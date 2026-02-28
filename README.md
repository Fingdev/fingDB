# fingDB - Central Database for Fing Projects

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/LibrecourseUY/fingDB)

Welcome to fingDB! This project is the centralized database for LibrecourseUY projects.

## What is this project?

fingDB is a database API that stores and serves common information used by different LibrecourseUY projects (like Fingcomms and Fingmap).

Basically, it's the "brain" that holds data shared between the various LibrecourseUY applications.

## Tech Stack

- **Language**: Python
- **Framework**: FastAPI
- **Database**: PostgreSQL (in production)
- **ORM**: SQLAlchemy
- **Dependency Management**: uv

## How to Install and Run

### Prerequisites

- Python 3.11 or higher
- PostgreSQL (optional, for local development)

### Local Development Setup

1. Clone the repository and enter the folder:
   ```bash
   cd fingdb
   ```

2. Install dependencies with uv:
   ```bash
   uv install
   ```

3. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Edit `.env` with your database configuration

4. Run database migrations:
   ```bash
   uv run alembic upgrade head
   ```

5. Start the development server:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

6. Visit `http://localhost:8000/docs` to see the API documentation

### With Docker

If you prefer using Docker:

```bash
docker build -t fingdb .
docker run -p 8000:8000 fingdb
```

## Project Structure

```
fingdb/
├── app/              # Main application code
│   ├── main.py       # Entry point
│   └── ...           # API modules
├── migrations/       # Database migrations
├── pyproject.toml    # Project configuration
└── uv.lock          # Dependency lockfile
```

## Graph Visualization

fingDB includes an interactive graph visualization that shows the prerequisite relationships between courses. This is particularly useful for students to understand:
- Which courses must be completed before taking another course
- The ideal sequence of courses throughout their career
- How different courses relate to each other

To access the graph:
1. Run the server: `uv run uvicorn app.main:app --reload`
2. Visit: `http://localhost:8000/graph`

For a detailed technical explanation of how the graph rendering works, see [graph.md](graph.md).

## How to Contribute

Want to add data or improve the API? Great!

Check out our contribution guide in [CONTRIBUTING.md](CONTRIBUTING.md).

## API Documentation

Once the server is running, you can view the automatic documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## License

MIT License - see [LICENSE](LICENSE)
