from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import ClauseElement
from iapservice.pyutil.testutil import OfflineError
import os

__all__ = [
    'OfflineError', # From iapservice.pyutil.testutil
    'CannotVerifyError',
    'InvalidIAPError',
    'InvalidGameError',
    'DBTableMixin',
    'find_file',
    'get_session',
    'default_session',
    'get_engine',
]

class InvalidGameError(Exception): pass
class CannotVerifyError(Exception): pass
class InvalidIAPError(Exception): pass

class DBTableMixin(object):
    """
    Utility mixin for SQLAlchemy
    """
    @classmethod
    def get(cls, session = None, **kwargs):
        if not session:
            session = default_session()
        return session.query(cls).filter_by(**kwargs).first()

    @classmethod
    def get_all(cls, session = None, **kwargs):
        if not session:
            session = default_session()
        return session.query(cls).filter_by(**kwargs).all()

    @classmethod
    def get_or_create(cls, session = None, defaults=None, **kwargs):
        """
        With slight modification:
        http://stackoverflow.com/questions/2546207/does-sqlalchemy-have-an-equivalent-of-djangos-get-or-create
        """
        if not session:
            session = default_session()
        defaults = defaults or {}
        #kwargs = { k : v for k,v in kwargs.iteritems() if cls.wrapped_column(k) in cls.__table__.columns }
        instance = session.query(cls).filter_by(**kwargs).first()
        if instance:
            return instance
        else:
            params = { k : v for k, v in kwargs.iteritems() if not isinstance(v, ClauseElement) }
            params.update(defaults)
            instance = cls(**params)
            session.add(instance)
            return instance

def find_file(filename):
    return os.path.join(os.environ['IAP_SERVICE_CONFIG'], filename)

_session = None
def get_session():
    global _session
    if not _session:
        _session = sessionmaker(bind=get_engine())
    return _session()

_default_session = None
def default_session():
    global _default_session
    if not _default_session:
        _default_session = get_session()
    return _default_session

_engine = None
def get_engine():
    global _engine
    if not _engine:
        with open(find_file('db_info'), 'r') as fp:
            _engine = create_engine(fp.readline())
    return _engine


