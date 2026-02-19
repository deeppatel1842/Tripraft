"""
Shared Declarative Base
Every ORM model in the application MUST import Base from here
so all table metadata lives in a single MetaData registry.
"""
from sqlalchemy.orm import declarative_base

Base = declarative_base()
