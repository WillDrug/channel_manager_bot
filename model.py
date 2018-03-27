
import os
from config import config
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref



Base = declarative_base()
engine = create_engine(
    config.db_conn,
    pool_recycle=280
)

class Channel(Base):
    __tablename__ = 'channels'

    id = Column(String(255), primary_key=True)  # chat id
    name = Column(String(255))  # channel name
    link = Column(String(50), nullable=True)  # for public channels
    owner = Column(Integer)  # creator

    modref = relationship("Mod", cascade="all, delete-orphan")

    def __repr__(self):
        return "<Channel(id='%s', name='%s', owner='%s', pinned_id='%s')>" % (
            self.id, self.name, self.owner, self.pinned_id
        )

class UserContext(Base):
    __tablename__ = 'contexts'

    id = Column(Integer, primary_key=True)
    channel = Column(String(255), ForeignKey('channels.id'), nullable=True)
    context = Column(String(20), nullable=True)
    next = Column(String(20), nullable=True)

    modref = relationship("Mod", cascade="all, delete-orphan")

    def __repr__(self):
        return "<UserContext(id='%s', chanenl='%s', context='%s', next='%s')>" % (
            self.id, self.channel, self.context, self.next
        )

class Mod(Base):
    __tablename__ = 'mods'

    id = Column(Integer, autoincrement=True, primary_key=True)
    channel = Column(String(255), ForeignKey('channels.id'))
    user = Column(Integer, ForeignKey('contexts.id'))



Base.metadata.create_all(engine)
new_session = sessionmaker(bind=engine)
