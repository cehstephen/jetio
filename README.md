# Jetio
![Jetio Logo](https://github.com/cehstephen/jetio/raw/main/jetio_main_logo.png)
### The Zero-Boilerplate Python Framework for Rapid API Development

[![PyPI version](https://badge.fury.io/py/jetio.svg)](https://badge.fury.io/py/jetio)
[![Python versions](https://img.shields.io/pypi/pyversions/jetio.svg)](https://pypi.org/project/jetio/)
[![License](https://img.shields.io/badge/license-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

**Jetio** is a modern, high-performance Python web framework designed to transform your SQLAlchemy models directly into fully-featured, production-ready REST APIs with minimal code. Stop writing boilerplate and start building what matters.

---

## Key Features

* **Model-Driven APIs:** Use standard SQLAlchemy models as your single source of truth for your database, validation, and API serialization.
* **Automatic CRUD:** Instantly generate robust Create, Read, Update, and Delete endpoints for any model with a single line of code.
* **Secure by Design:** Easily secure your auto-generated endpoints with a single flag and plug in your own authentication logic.
* **Async First:** Built from the ground up on an async core (powered by Starlette) for maximum performance and scalability.
* **Automatic Docs:** Get interactive and functional Swagger UI out of the box.
* **Flexible & Familiar:** Escape the generator whenever you need to. Use familiar decorator-based routing for custom endpoints, giving you the best of both worlds.

---

- **Visit Jetio Framework** [You can deliver more than 500 times faster with Jetio - see how it works.](https://jetio.org)
- **Jetio Framework oneBenchmark Results:** [We compared Jetio speed with Flask & FastAPI](https://jetio.org/jetio_benchmark_report.html) See the result for yourself.
---

## Simple Hello Jetio app
```python
from jetio import Jetio
app = Jetio()

@app.route('/')
async def hello():
    return "Hello, Jetio!"

if __name__ == '__main__':
    app.run()

```

## Example - Using models in separate file
```python
# model.py
from sqlalchemy.orm import Mapped
from jetio import JetioModel

class User(JetioModel):
    username: Mapped[str]
    email: Mapped[str]

class Minister(JetioModel):
    first_name: Mapped[str]
    last_name: Mapped[str]
```

### Get Jetio to make your app with imported models
```python
# app.py
from jetio import Jetio, CrudRouter, add_swagger_ui
from model import User, Minister

app = Jetio()
add_swagger_ui(app)

# Generate 5 CRUD routes per model
CrudRouter(model=User).register_routes(app)
CrudRouter(model=Minister).register_routes(app)


if __name__ == "__main__":
    app.run()
```

## Database setup 
Use your preferred DB tool.

_or for quick dev environment, you can also change your app.py above to:_
```python
# app.py
from jetio import Jetio, CrudRouter, add_swagger_ui, Base, engine
from model import User, Minister
import asyncio

app = Jetio()
add_swagger_ui(app)

# Generate 5 CRUD routes per model
CrudRouter(model=User).register_routes(app)
CrudRouter(model=Minister).register_routes(app)


# --- Database and Server Startup ---
async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created.")

if __name__ == "__main__":
    asyncio.run(create_db_and_tables())
    app.run()
```

### Simplified Single File Setup
You could simply have the model classes in the main file as follows.
```python

from jetio import Jetio, CrudRouter, JetioModel, add_swagger_ui, Base, engine
import asyncio
from sqlalchemy.orm import Mapped

class Staff(JetioModel):
    username: Mapped[str]
    email: Mapped[str]

class Report(JetioModel):
    title: Mapped[str]
    content: Mapped[str]

app = Jetio()
add_swagger_ui(app)

# Generate 5 CRUD routes per model
CrudRouter(model=Staff).register_routes(app)
CrudRouter(model=Report).register_routes(app)


# --- Database and Server Startup ---
async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created.")

if __name__ == "__main__":
    asyncio.run(create_db_and_tables())
    app.run()

```

The CrudRouter is a powerful tool that allows you to cleanly declare your API's functionality, saving you from writing hundreds of lines of boilerplate code.

## Relationship
Jetio relationship prevents N+1 Query - Built-in relationship loading using SQLAlchemy's selectinload() prevents performance bottlenecks automatically.

### One-to-many Relationship
```python
# app.py
from jetio import Jetio, CrudRouter, JetioModel, add_swagger_ui, Base, engine
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
import asyncio

#===================================================================
# Models - you can have this in a separate file, however you desire.
#===================================================================
class Author(JetioModel):
    __tablename__ = 'authors'
    name: Mapped[str]
    email: Mapped[str]
    books: Mapped[List["Book"]] = relationship(back_populates="author", cascade="all, delete-orphan")


class Book(JetioModel):
    __tablename__ = 'books'
    title: Mapped[str]
    isbn: Mapped[str]
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"))
    author: Mapped["Author"] = relationship(back_populates="books")
#===========================================
# end of models
# =========================================

app = Jetio()
add_swagger_ui(app)

CrudRouter(model=Author, load_relationships=["books"]).register_routes(app)
CrudRouter(model=Book, load_relationships=["author"]).register_routes(app)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database initialized")

if __name__ == "__main__":
    asyncio.run(init_db())
    print("🚀 Server running at http://localhost:8000")
    print("📚 API docs at http://localhost:8000/docs")
    app.run()
```

## Our Philosophy

Boilerplate code is a barrier between a great idea and a finished product. Modern development should be about defining your logic, not endlessly reimplementing the plumbing. Jetio believes in convention over configuration and the power of using a single source of truth. Your data model is your API.

## Contributing

Contributions are welcome! Please feel free to submit a pull request, open an issue, or provide feedback.

## License

This project is licensed under the BSD 3-Clause license.
