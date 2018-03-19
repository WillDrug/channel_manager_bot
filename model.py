import os
from config import config
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

connection_string = config.db_conn % os.environ.get('SQLPWD')
print(connection_string)
Base = declarative_base()
engine = create_engine(
    connection_string,
    pool_recycle=280
)


class Channel(Base):
    __tablename__ = 'channels'

    id = Column(String(255), primary_key=True)
    name = Column(String(255))

    def __repr__(self):
        return "<Channel(id='%s', name='%s')>" % (
            self.id, self.name
        )

Base.metadata.create_all(engine)
Session = sessionmaker()
Session.configure(bind=engine)
session = Session()
