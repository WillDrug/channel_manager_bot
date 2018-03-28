
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

class Mod(Base):
    __tablename__ = 'mods'

    id = Column(Integer, autoincrement=True, primary_key=True)
    channel = Column(String(255), ForeignKey('channels.id'))
    user = Column(Integer, ForeignKey('contexts.id'))

class Ban(Base):
    __tablename__ = 'banned'

    id = Column(Integer, autoincrement=True, primary_key=True)
    channel = Column(String(255), ForeignKey('channels.id'))
    user = Column(Integer, ForeignKey('contexts.id'))
    # TODO: think about fixing. Theoretically if you find how to destroy your UserContext data -- you are unbanned

class Message(Base):
    __tablename__ = 'messages'

    # id = Column(Integer, autoincrement=True, primary_key=True)
    from_id = Column(Integer, ForeignKey('contexts.id'), primary_key=True)
    message_id = Column(Integer, primary_key=True)
    channel = Column(String(255), ForeignKey('channels.id'))
    assigned_mod = Column(Integer, ForeignKey('contexts.id'))
    # ... ? TODO: update or bot updates will kill shit.

class Channel(Base):
    __tablename__ = 'channels'

    id = Column(String(255), primary_key=True)  # chat id
    name = Column(String(255))  # channel name
    link = Column(String(50), nullable=True)  # for public channels
    owner = Column(Integer)  # creator

    modref = relationship("Mod", cascade="all, delete-orphan")
    banref = relationship("Ban", cascade="all, delete-orphan")
    msgref = relationship("Message", cascade="all, delete-orphan")

    def __repr__(self):
        return "<Channel(id='%s', name='%s', link='%s', owner='%s')>" % (
            self.id, self.name, self.link, self.owner
        )



class UserContext(Base):
    __tablename__ = 'contexts'

    id = Column(Integer, primary_key=True)
    username = Column(String(100))
    channel = Column(String(255), ForeignKey('channels.id'), nullable=True)
    context = Column(String(20), nullable=True)
    next = Column(String(20), nullable=True)

    modref = relationship("Mod", cascade="all, delete-orphan")
    banref = relationship("Ban", cascade="all, delete-orphan")
    msgref = relationship("Message", cascade="all, delete-orphan")

    def __repr__(self):
        return "<UserContext(id='%s', chanenl='%s', context='%s', next='%s')>" % (
            self.id, self.channel, self.context, self.next
        )



Base.metadata.create_all(engine)
new_session = sessionmaker(bind=engine)
