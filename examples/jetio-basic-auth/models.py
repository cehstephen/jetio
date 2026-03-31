from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jetio import JetioModel
from jetio_auth import JetioAuthMixin


class User(JetioModel, JetioAuthMixin):
    __tablename__ = "example1_users"

    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(unique=True)


class Post(JetioModel):
    __tablename__ = "example1_posts"

    title: Mapped[str]
    content: Mapped[str]
    author_id: Mapped[int] = mapped_column(ForeignKey("example1_users.id"))
    author: Mapped[User] = relationship()
