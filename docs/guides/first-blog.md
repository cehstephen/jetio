# Your First Blog with Jetio

In this guide, you’ll build a simple Question & Answer blog API using Jetio.

The goal is to show how quickly you can:

- define models

- generate CRUD APIs

- explore your API using Swagger UI

We’ll intentionally keep configuration minimal so you can focus on Jetio itself.


## What You’ll Build

By the end of this guide, you will have:

- A running Jetio API

- Models for Users, Questions, and Answers

- Fully working CRUD endpoints (no boilerplate)

- Automatic Swagger documentation

## Prerequisites

- Python 3.8+

- pip


## Project Setup

1. Create a project
    ```
    mkdir jetio_blog
    cd jetio_blog
    ```
    
2. Create and activate a virtual environment
    ```
    python3 -m venv venv
    ```
    Activate it:

    - Windows: venv\Scripts\activate

    - macOS/Linux: source venv/bin/activate

3. Install dependencies
    - create file requirements.txt
    
    - add the following two lines to the file
    ```
    jetio
    uvicorn
   ```

    - Install:
    ``` pip install -r requirements.txt ```

    ℹ️ Jetio uses SQLite by default, which is perfect for development.
    For PostgreSQL or MySQL, see Configuration → Database Setup.

## Defining the Models (models.py)
Create models.py:
```python
from jetio import JetioModel, relationship
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, func
from datetime import datetime
from typing import List

class User(JetioModel):
    username: Mapped[str]
    email: Mapped[str]
    questions: Mapped[List["Question"]] = relationship(back_populates="user")
    answers: Mapped[List["Answer"]] = relationship(back_populates="user")

class Question(JetioModel):
    title: Mapped[str]
    content: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="questions")
    answers: Mapped[List["Answer"]] = relationship(back_populates="question")
    created_at: Mapped[datetime] = mapped_column(default=func.now())

class Answer(JetioModel):
    content: Mapped[str]
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    question: Mapped["Question"] = relationship(back_populates="answers")
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="answers")
    created_at: Mapped[datetime] = mapped_column(default=func.now())
```

## Why this works

- JetioModel automatically creates:

  - database tables
  - Pydantic schemas for API input/output

- Relationships are handled by SQLAlchemy
- Jetio exposes relationships cleanly in API responses


## Creating the Application (app.py)

Create app.py:
```python
from jetio import Jetio, CrudRouter, add_swagger_ui, Base, engine
import asyncio
from models import User, Question, Answer

app = Jetio(title="Jetio Blog")
add_swagger_ui(app) # Optional: enables Swagger UI at /docs

CrudRouter(User, load_relationships=["questions", "answers"]).register_routes(app)
CrudRouter(Question, load_relationships=["user", "answers"]).register_routes(app)
CrudRouter(Answer, load_relationships=["question", "user"]).register_routes(app)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(init_db())
    app.run()
```

⚠️ This example uses automatic table creation for development.
For migrations and production setups, see Configuration → Database Setup.


## Running the App
```python app.py ```

- Visit:

    - API: http://localhost:8000

    - Docs: http://localhost:8000/do


## Using the API

Jetio automatically creates standard REST endpoints for each model
(e.g. `/users`, `/questions`, `/answers`).

You can explore all available endpoints interactively at `/docs`.


You can:

- create users

-  post questions and answers

- retrieve related data

- update and delete records

All directly from Swagger UI.

## What You Learned

- How Jetio models work

- How CRUD APIs are generated automatically

- How relationships are exposed in APIs

- How Swagger UI is integrated by default

## Next Steps

Continue with:

- Authentication & Authorization

- Securing CRUD routes

- Database configuration

- Deploying Jetio applications

➡️ See Configuration → Database Setup to move beyond SQLite.