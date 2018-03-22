import os
from config import config
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship



Base = declarative_base()
engine = create_engine(
    config.db_conn,
    pool_recycle=280
)


class Channel(Base):
    __tablename__ = 'channels'

    id = Column(String(255), primary_key=True)
    name = Column(String(255))  #mnemonic
    owner = Column(Integer)
    pinned_id = Column(Integer, nullable=True)
    modlist = relationship("Mod", cascade="all, delete-orphan")
    banlist = relationship("Banned", cascade="all, delete-orphan")
    invitelist = relationship("Invite", cascade="all, delete-orphan")
    messagequeue = relationship("Message", cascade="all, delete-orphan")

    def __repr__(self):
        return "<Channel(id='%s', name='%s')>" % (
            self.id, self.name
        )

class UserContext(Base):
    __tabename__ = 'contexts'

    id = Column(Integer, primary_key=True)
    username = Column(String(255))
    menu = Column(String(25))
    channel = Column(String(255), ForeignKey('channels.id'))  # TODO: delete this, there's no need for complex contexts

class Mod(Base):
    __tablename__ = 'moderators'

    channel = Column(String(255), ForeignKey('channels.id'))
    mod_id = Column(Integer)

class Banned(Base):
    __tablename__ = 'banlist'

    channel = Column(String(255), ForeignKey('channels.id'))
    user = Column(Integer)

class Invite(Base):
    __tablename__ = 'invites'

    invite_hash = Column(String(38), primary_key=True)
    channel = Column(String(255), ForeignKey('channels.id'))

class Message(Base):
    __tablename__ = 'messages'

    from_id = Column(Integer)
    from_username = Column(String(255))
    message_id = Column(Integer)
    channel = Column(String(255), ForeignKey('channels.id'))
    submitted_on = Column(Integer)
    published_on = Column(Integer)


Base.metadata.create_all(engine)
session = sessionmaker(bind=engine)()
