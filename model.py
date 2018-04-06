
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

class Bullshit(Base):
    __tablename__ = 'bullshit'

    id = Column(String(100), primary_key=True)  # user id or user channel sign.
    counter = Column(Integer, default=0)
    took_the_piss_at = Column(Integer, nullable=True)
    sent_warning = Column(Boolean, nullable=True, default=False)
    def __repr__(self):
        return "<Bullshit(id='%s', counter='%s', piss='%s', warning='%s')>" % (
            self.id, self.counter, self.took_the_piss_at, self.sent_warning
        )
class Mod(Base):
    __tablename__ = 'mods'

    id = Column(Integer, autoincrement=True, primary_key=True)
    channel = Column(String(255), ForeignKey('channels.id', ondelete='CASCADE'))
    user = Column(Integer, ForeignKey('contexts.id', ondelete='CASCADE'))

    def __repr__(self):
        return "<Mod(id='%s', chanenl='%s', user='%s')>" % (
            self.id, self.channel, self.user
        )

class Ban(Base):
    __tablename__ = 'banned'

    id = Column(Integer, autoincrement=True, primary_key=True)
    channel = Column(String(255), ForeignKey('channels.id', ondelete='CASCADE'))
    user = Column(Integer, ForeignKey('contexts.id', ondelete='CASCADE'))
    # TODO: think about fixing. Theoretically if you find how to destroy your UserContext data -- you are unbanned
    def __repr__(self):
        return "<Ban(id='%s', chanenl='%s', user='%s')>" % (
            self.id, self.channel, self.user
        )

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, autoincrement=True, primary_key=True)
    from_id = Column(Integer, ForeignKey('contexts.id', ondelete='CASCADE'))
    message_id = Column(Integer)
    channel = Column(String(255), ForeignKey('channels.id', ondelete='CASCADE'))
    assigned_mod = Column(Integer, nullable=True)  #ForeignKey('contexts.id'),
    assigned_id = Column(Integer, nullable=True)
    submit_on = Column(Integer, nullable=True)
    # ... ? TODO: update or bot updates will kill shit.
    def __repr__(self):
        return "<Message(id='%s', from_id='%s', message_id='%s', channel='%s', assigned_mod='%s', assigned_id='%s', submit_on='%s')>" % (
            self.id, self.from_id, self.message_id, self.channel, self.assigned_mod, self.assigned_id, self.submit_on
        )

class Invite(Base):
    __tablename__ = 'invites'

    channel = Column(String(255), ForeignKey('channels.id', ondelete='CASCADE'), primary_key=True)
    code = Column(String(36), primary_key=True)

    def __repr__(self):
        return "<Invite(channel='%s', code='%s')>" % (
            self.channel, self.code
        )

class Channel(Base):
    __tablename__ = 'channels'

    id = Column(String(255), primary_key=True)  # chat id
    name = Column(String(255))  # channel name
    link = Column(String(50), nullable=True)  # for public channels
    owner = Column(Integer)  # creator

    modref = relationship("Mod", cascade="all, delete-orphan")
    banref = relationship("Ban", cascade="all, delete-orphan")
    msgref = relationship("Message", cascade="all, delete-orphan")
    invref = relationship("Invite", cascade="all, delete-orphan")

    def __repr__(self):
        return "<Channel(id='%s', name='%s', link='%s', owner='%s')>" % (
            self.id, self.name, self.link, self.owner
        )



class UserContext(Base):
    __tablename__ = 'contexts'

    id = Column(Integer, primary_key=True)
    username = Column(String(100))
    channel = Column(String(255), ForeignKey('channels.id', ondelete='CASCADE'), nullable=True)
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
