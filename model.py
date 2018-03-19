
from config import config
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
engine = create_engine(
    config.db_conn,
    pool_recycle=280
)


class Channel(Base):
    __tablename__ = 'channels'

    id = Column(String, primary_key=True)
    name = Column(String)

    def __repr__(self):
        return "<Channel(id='%s', name='%s')>" % (
            self.id, self.name
        )

Base.metadata.create_all(engine)
Session = sessionmaker()
Session.configure(bind=engine)
session = Session()
