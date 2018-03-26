
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

    id = Column(Integer, primary_key=True)
    counter = Column(Integer)
    added = Column(Integer, nullable=True)


class Channel(Base):
    __tablename__ = 'channels'

    id = Column(String(255), primary_key=True)
    name = Column(String(255))  #mnemonic
    link = Column(String(50), nullable=True)
    owner = Column(Integer)
    pinned_id = Column(Integer, nullable=True)

    modlist = relationship("Mod", cascade="all, delete-orphan")
    banlist = relationship("Banned", cascade="all, delete-orphan")
    invitelist = relationship("Invite", cascade="all, delete-orphan")
    messagequeue = relationship("Message", cascade="all, delete-orphan")

    def __repr__(self):
        return "<Channel(id='%s', name='%s', owner='%s', pinned_id='%s')>" % (
            self.id, self.name, self.owner, self.pinned_id
        )

class UserContext(Base):
    __tablename__ = 'contexts'

    id = Column(Integer, primary_key=True)
    username = Column(String(255))
    menu = Column(String(25))
    channel = Column(String(255), ForeignKey('channels.id'), nullable=True)

    def __repr__(self):
        return "<UserContext(id='%s', username='%s', menu='%s', channel='%s')>" % (
            self.id, self.username, self.menu, self.channel
        )

class Mod(Base):
    __tablename__ = 'moderators'

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel = Column(String(255), ForeignKey('channels.id'))
    mod_id = Column(Integer)
    mod_name = Column(String(255))

    #messages = relationship('Message', backref=backref('messages.assigned_mod'))

class Banned(Base):
    __tablename__ = 'banlist'
    id = Column(Integer, primary_key=True, autoincrement=True)
    channel = Column(String(255), ForeignKey('channels.id'))
    user = Column(Integer)
    username = Column(String(255))

class Invite(Base):
    __tablename__ = 'invites'

    #query_id = Column(String(50), primary_key=True)
    invite_hash = Column(String(38), primary_key=True)
    channel = Column(String(255), ForeignKey('channels.id'))

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_id = Column(Integer)
    from_username = Column(String(255), nullable=True)
    message_id = Column(Integer)
    channel = Column(String(255), ForeignKey('channels.id'), nullable=True)
    show_username = Column(Boolean, default=False)
    assigned_mod = Column(Integer, nullable=True)  # foreign key to Mod - mod_id. too lazy to properly add
    submitted_on = Column(Integer, nullable=True)
    published_on = Column(Integer, nullable=True)
    current_request = Column(Integer, nullable=True)


Base.metadata.create_all(engine)
new_session = sessionmaker(bind=engine)
