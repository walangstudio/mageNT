"""FastAPI project scaffolding skill."""

from typing import Any, Dict, List

try:
    from skills.base import BaseSkill
except ImportError:
    from ..base import BaseSkill


class ScaffoldFastAPI(BaseSkill):
    """Scaffold a new FastAPI project with modern Python practices."""

    @property
    def name(self) -> str:
        return "scaffold_fastapi"

    @property
    def slash_command(self) -> str:
        return "/scaffold-fastapi"

    @property
    def description(self) -> str:
        return "Create a new FastAPI project with async support, Pydantic, and modern tooling"

    @property
    def category(self) -> str:
        return "scaffold"

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "project_name",
                "type": "string",
                "description": "Name of the project to create",
                "required": True,
            },
            {
                "name": "database",
                "type": "string",
                "description": "Database: sqlalchemy, tortoise, or none",
                "required": False,
            },
            {
                "name": "auth",
                "type": "string",
                "description": "Authentication: jwt, oauth2, or none",
                "required": False,
            },
            {
                "name": "package_manager",
                "type": "string",
                "description": "Package manager: uv, poetry, or pip",
                "required": False,
            },
        ]

    def execute(self, **kwargs) -> Dict[str, Any]:
        project_name = kwargs.get("project_name", "my-fastapi-app")
        database = kwargs.get("database", "sqlalchemy")
        auth = kwargs.get("auth", "jwt")
        pkg_manager = kwargs.get("package_manager", "uv")

        guidance = f"""# FastAPI Project Scaffolding Guide

## Project: {project_name}

### Step 1: Create Project Structure
```bash
mkdir {project_name}
cd {project_name}
"""

        if pkg_manager == "uv":
            guidance += """
# Initialize with uv (recommended)
uv init
uv add fastapi uvicorn[standard] pydantic pydantic-settings
```
"""
        elif pkg_manager == "poetry":
            guidance += """
# Initialize with Poetry
poetry init -n
poetry add fastapi uvicorn[standard] pydantic pydantic-settings
```
"""
        else:
            guidance += """
# Initialize with pip
python -m venv venv
source venv/bin/activate  # or venv\\Scripts\\activate on Windows
pip install fastapi uvicorn[standard] pydantic pydantic-settings
```
"""

        guidance += """
### Step 2: Install Additional Dependencies
"""

        # Database
        if database == "sqlalchemy":
            if pkg_manager == "uv":
                guidance += """
#### SQLAlchemy + Alembic
```bash
uv add sqlalchemy asyncpg alembic
```
"""
            else:
                guidance += """
#### SQLAlchemy + Alembic
```bash
pip install sqlalchemy asyncpg alembic
```
"""

            guidance += """
Initialize Alembic:
```bash
alembic init alembic
```

Example models (`app/models/user.py`):
```python
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

Database connection (`app/db/session.py`):
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```
"""
        elif database == "tortoise":
            if pkg_manager == "uv":
                guidance += """
#### Tortoise ORM
```bash
uv add tortoise-orm aerich asyncpg
```
"""
            else:
                guidance += """
#### Tortoise ORM
```bash
pip install tortoise-orm aerich asyncpg
```
"""

        # Auth
        if auth == "jwt":
            if pkg_manager == "uv":
                guidance += """
#### JWT Authentication
```bash
uv add python-jose[cryptography] passlib[bcrypt]
```
"""
            else:
                guidance += """
#### JWT Authentication
```bash
pip install python-jose[cryptography] passlib[bcrypt]
```
"""

            guidance += """
Auth utilities (`app/core/security.py`):
```python
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
```
"""

        guidance += f"""
### Step 3: Project Structure
```
{project_name}/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py          # Dependencies
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py    # API router
│   │       └── endpoints/
│   │           ├── users.py
│   │           └── auth.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Settings
│   │   └── security.py      # Auth utilities
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py          # SQLAlchemy base
│   │   └── session.py       # DB session
│   ├── models/              # SQLAlchemy models
│   │   └── user.py
│   ├── schemas/             # Pydantic schemas
│   │   └── user.py
│   └── services/            # Business logic
│       └── user.py
├── alembic/
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── api/
├── .env
├── alembic.ini
└── pyproject.toml
```

### Step 4: Main Application
Create `app/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{{settings.API_V1_STR}}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {{"status": "healthy"}}
```

### Step 5: Configuration
Create `app/core/config.py`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "{project_name}"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/db"

    class Config:
        env_file = ".env"

settings = Settings()
```

### Step 6: Development
```bash
uvicorn app.main:app --reload
```

API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Recommended Additions
- pytest + httpx for testing
- Ruff for linting
- Pre-commit hooks
- Docker + docker-compose
"""

        return {
            "guidance": guidance,
            "context": {
                "project_name": project_name,
                "database": database,
                "auth": auth,
                "package_manager": pkg_manager,
            },
            "success": True,
        }
