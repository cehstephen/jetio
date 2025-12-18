# Your First Blog with Jetio

Welcome to this tutorial on building a Question & Answer blog using the Jetio framework. This guide is designed for beginners, especially those who are new to Jetio and may not have extensive experience with SQLAlchemy. We will walk through the code step-by-step, explaining the concepts in a clear and professional manner.

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.8+
- `pip` (Python's package installer)

## Setup

1.  **Create a Project Directory:**
    ```bash
    mkdir jetio_blog
    cd jetio_blog
    ```

2.  **Create a Virtual Environment:**
    It's a best practice to create a virtual environment for your project to manage dependencies.
    ```bash
    python -m venv venv
    ```
    Activate the virtual environment:
    -   **Windows:** `venv\Scripts\activate`
    -   **macOS/Linux:** `source venv/bin/activate`

3.  **Install Dependencies:**
    Create a `requirements.txt` file with the following content:
    ```
    jetio
    uvicorn
    ```
    Now, install these dependencies using pip:
    ```bash
    pip install -r requirements.txt
    ```

## Configuring the Database

By default, Jetio uses SQLite, which is a simple file-based database perfect for development. For production environments, you'll likely want to use a more robust database like PostgreSQL or MySQL. Jetio is built on SQLAlchemy, so it supports any database that SQLAlchemy supports.

Configuration is done via a `DATABASE_URL` environment variable.

### Using a .env File for Configuration

Setting environment variables manually every time you start your application can be tedious. A common and recommended practice is to use a `.env` file to store your configuration variables.

Jetio has built-in support for `.env` files using the `python-dotenv` library.

1.  **Install `python-dotenv`:**
    Add `python-dotenv` to your `requirements.txt` and install it.

    ```
    # requirements.txt
    jetio
    uvicorn
    python-dotenv
    # Add your database driver below, e.g., psycopg2-binary
    ```
    ```bash
    pip install -r requirements.txt
    ```

2.  **Create a `.env` file:**
    In the root of your project, create a file named `.env`. **Important: Never commit this file to version control (e.g., git) as it contains sensitive credentials.** Add it to your `.gitignore` file.

    Your `.env` file should look like this:
    ```
    # .env
    DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/blogdb"
    ```

Now, when you run your application, Jetio will automatically load the `DATABASE_URL` from the `.env` file. You no longer need to set it manually in your shell.

### Using PostgreSQL

1.  **Install the Driver:**
    You need to install the `psycopg2` driver, which allows SQLAlchemy to communicate with PostgreSQL. It's recommended to use `psycopg2-binary` for ease of installation.

    Add it to your `requirements.txt` (if you haven't already) and install it:
    ```
    # requirements.txt
    jetio
    uvicorn
    python-dotenv
    psycopg2-binary
    ```
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set the `DATABASE_URL`:**
    As described above, create a `.env` file with the PostgreSQL connection string:
    `postgresql+asyncpg://<user>:<password>@<host>:<port>/<database>`

    Example `.env` file:
    ```
    # .env
    DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/blogdb"
    ```
    
    *Note: Jetio uses `asyncpg` for its asynchronous operations with PostgreSQL.*

### Using MySQL

1.  **Install the Driver:**
    For MySQL, you'll need an asynchronous driver. `aiomysql` is a good choice.

    Add it to `requirements.txt` and install:
    ```
    # requirements.txt
    jetio
    uvicorn
    python-dotenv
    aiomysql
    ```
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set the `DATABASE_URL`:**
    Create a `.env` file with the MySQL connection string:
    `mysql+aiomysql://<user>:<password>@<host>:<port>/<database>`

    Example `.env` file:
    ```
    # .env
    DATABASE_URL="mysql+aiomysql://user:password@localhost:3306/blogdb"
    ```
      
*Note: You must create the database (`blogdb` in these examples) in PostgreSQL or MySQL before running the application.*



## Understanding the Models (`models.py`)

Our blog will have Users, Questions, and Answers. We need to create data models for each of these. In Jetio, models are defined using SQLAlchemy's ORM (Object-Relational Mapping), but with the simplicity of Jetio's `JetioModel`.

Create a file named `models.py`:

```python
from jetio import JetioModel, relationship
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import List
from sqlalchemy import \
    ForeignKey,
    func,
)

class User(JetioModel):
    __tablename__ = 'users'
    username: Mapped[str]
    email: Mapped[str]
    questions: Mapped[List["Question"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    answers: Mapped[List["Answer"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Question(JetioModel):
    __tablename__ = 'questions'
    title: Mapped[str]
    content: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="questions")
    answers: Mapped[List["Answer"]] = relationship(back_populates="question", cascade="all, delete-orphan")
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())


class Answer(JetioModel):
    __tablename__ = 'answers'
    content: Mapped[str]
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    question: Mapped["Question"] = relationship(back_populates="answers")
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="answers")
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
```

### Explanation of `models.py`:

-   **`JetioModel`**: This is the base model from Jetio that our models inherit from. It provides the basic structure and functionality, including an `id` field by default.
-   **`__tablename__`**: This attribute specifies the name of the database table for the model.
-   **`Mapped[type]`**: This is a type hint from SQLAlchemy that indicates a field is mapped to a database column. For example, `Mapped[str]` defines a string column.
-   **`mapped_column`**: This function is used for more complex column definitions, such as setting a default value or defining a foreign key.
-   **`relationship`**: This is the most powerful feature. It defines the relationship between models. For example, in the `User` model, `questions: Mapped[List["Question"]] = relationship(...)` tells SQLAlchemy that a User can have multiple Questions.
-   **`ForeignKey`**: This is a constraint that links a column in one table to a column in another table. For example, `user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))` in the `Question` model links each question to a user.
-   **`back_populates`**: This parameter in `relationship` links two relationships together. For instance, the `questions` relationship in `User` is linked to the `user` relationship in `Question`. This allows you to access the related objects from either side.
-   **`cascade="all, delete-orphan"`**: This tells the database what to do when an object is deleted. In our case, if a `User` is deleted, all their `Question`s and `Answer`s will also be deleted.

## The Application Logic (`app.py`)

Now, let's create the main application file, `app.py`. This file will initialize the Jetio application, set up the API routes, and configure the database.

```python
from jetio import Jetio, CrudRouter, add_swagger_ui, Base, engine

import asyncio
from models import Question, Answer, User

app = Jetio(title="Blog with Jetio")
add_swagger_ui(app)

CrudRouter(model=User, load_relationships=["questions", "answers"]).register_routes(app)
CrudRouter(model=Question, load_relationships=["user", "answers"]).register_routes(app)
CrudRouter(model=Answer, load_relationships=["question", "user"]).register_routes(app)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database initialized")

if __name__ == "__main__":
    asyncio.run(init_db())
    print("🚀 Server running at http://localhost:8000")
    print("📚 API docs at http://localhost:8000/docs")
    app.run()
```

### Explanation of `app.py`:

-   **`app = Jetio(title="Blog with Jetio")`**: This creates an instance of the Jetio application. The `title` will be used in the API documentation.
-   **`add_swagger_ui(app)`**: This is a handy utility from Jetio that automatically generates interactive API documentation (Swagger UI) for your application.
-   **`CrudRouter`**: This is where the magic of Jetio happens. `CrudRouter` automatically creates the Create, Read, Update, and Delete (CRUD) API endpoints for a given model.
    -   `model=User`: We specify the model we want to create routes for.
    -   `load_relationships=[...]`: This tells `CrudRouter` to include the specified relationships when fetching data. For example, when you get a `User`, it will also include their `questions` and `answers`.
    -   `.register_routes(app)`: This registers the generated routes with our Jetio application.
-   **`init_db()`**: This asynchronous function initializes the database.
    -   `Base.metadata.drop_all`: This drops all existing tables. This is useful for development to start with a clean slate each time. **You should remove this in a production environment.**
    -   `Base.metadata.create_all`: This creates all the tables defined in our models.
-   **`if __name__ == "__main__":`**: This is standard Python practice. The code inside this block will only run when you execute `python app.py`.
    -   `asyncio.run(init_db())`: We run the database initialization.
    -   `app.run()`: This starts the web server.

## Running the Application

To run your blog application, simply run the `app.py` file:

```bash
python app.py
```

You should see output indicating that the server is running:

```
✅ Database initialized
🚀 Server running at http://localhost:8000
📚 API docs at http://localhost:8000/docs
```

## Using the API

Jetio has automatically created a fully functional REST API for our blog. You can explore and interact with it using the Swagger UI documentation.

Open your web browser and go to **http://localhost:8000/docs**.

You will see a beautiful, interactive API documentation page where you can:
-   Create users
-   Post questions
-   Post answers to questions
-   Read, update, and delete users, questions, and answers.

### Example API usage with `curl`:

Here's how you can interact with your API from the command line using `curl`.

1.  **Create a User:**
    ```bash
    curl -X 'POST' \
      'http://localhost:8000/users' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
      "username": "testuser",
      "email": "test@example.com"
    }'
    ```

2.  **Post a Question:** (Assuming the user created above has an ID of 1)
    ```bash
    curl -X 'POST' \
      'http://localhost:8000/questions' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
      "title": "What is Jetio?",
      "content": "I would like to know more about the Jetio framework.",
      "user_id": 1
    }'
    ```

3.  **Post an Answer:** (Assuming the question has an ID of 1 and the user has an ID of 1)
    ```bash
    curl -X 'POST' \
      'http://localhost:8000/answers' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
      "content": "Jetio is a modern Python web framework for building APIs with ease.",
      "question_id": 1,
      "user_id": 1
    }'
    ```

4.  **Get a Question and its Answers:**
    ```bash
    curl -X 'GET' 'http://localhost:8000/questions/1' -H 'accept: application/json'
    ```
    The output will be a JSON object for the question, and because we used `load_relationships`, it will also contain a list of its answers.

## Conclusion

Congratulations! You have successfully built a fully functional Q&A blog API using Jetio. As you can see, Jetio allows for rapid development by automating the creation of CRUD APIs, while still providing the power and flexibility of SQLAlchemy for data modeling.

From here, you could build a frontend application (e.g., using React, Vue, or another framework) that interacts with your new Jetio API. Happy coding!
