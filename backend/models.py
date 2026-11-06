
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Enum,
    DateTime,
    ForeignKey,
    Boolean,
    func
)

from sqlalchemy.orm import relationship

from database import Base


# User Model
class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    username = Column(String(100), nullable=False)

    email = Column(String(150), unique=True, nullable=False)

    password = Column(String(255), nullable=False)

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp()
    )

    # Relationships
    tasks = relationship(
        "Task",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    notes = relationship(
        "Note",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    schedules = relationship(
        "Schedule",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    reminders = relationship(
        "Reminder",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True
    )


# Task Model
class Task(Base):

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    title = Column(String(255), nullable=False)

    description = Column(Text, nullable=True)

    status = Column(
        Enum("Pending", "In Progress", "Completed", name="task_status"),
        default="Pending"
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp()
    )

    owner = relationship("User", back_populates="tasks")


# Note Model
class Note(Base):

    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    title = Column(String(255), nullable=False)

    content = Column(Text, nullable=False)

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp()
    )

    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )

    owner = relationship("User", back_populates="notes")


# Schedule Model
class Schedule(Base):

    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    title = Column(String(255), nullable=False)

    description = Column(Text, nullable=True)

    start_time = Column(DateTime, nullable=False)

    end_time = Column(DateTime, nullable=False)

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp()
    )

    owner = relationship("User", back_populates="schedules")


# Reminder Model
class Reminder(Base):

    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    title = Column(String(255), nullable=False)

    description = Column(Text, nullable=True)

    remind_at = Column(DateTime, nullable=False)

    is_sent = Column(Boolean, default=False, nullable=False)

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp()
    )

    owner = relationship("User", back_populates="reminders")
