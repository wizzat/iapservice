from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import ClauseElement
from sqlalchemy.schema import UniqueConstraint
from iapservice.util import *
from pyutil.dateutil import now
import os, json, requests

Base = declarative_base()

__all__ = [
    'Company',
    'Game',
    'IOSPackage',
    'IOSTransaction',
    'User',
    'Status',
]

class Company(DBTableMixin, Base):
    __tablename__ = 'companies'

    id   = Column(Integer, primary_key = True)
    name = Column(String, unique = True, nullable = False)

class Game(DBTableMixin, Base):
    __tablename__ = 'games'

    id          = Column(Integer, primary_key = True)
    company_id  = Column(Integer, ForeignKey('companies.id'))
    game_secret = Column(String, unique = True)
    name        = Column(String, unique = True)

class IOSPackage(DBTableMixin, Base):
    __tablename__ = 'packages'

    id               = Column(Integer, primary_key = True)
    game_id          = Column(Integer, ForeignKey('games.id'))
    company_id       = Column(Integer, ForeignKey('companies.id'))
    reported_package = Column(String)
    local_value      = Column(Float)
    effective_date   = Column(DateTime)
    expiration_date  = Column(DateTime)

    UniqueConstraint('game_id', 'reported_package', 'effective_date')

class User(DBTableMixin, Base):
    __tablename__ = 'users'

    id         = Column(Integer, primary_key = True)
    ifa        = Column(String)   # Client IFA
    ifv        = Column(String)   # Client IFV
    created_on = Column(DateTime) # Server TS
    game_id    = Column(Integer, ForeignKey('games.id'))
    company_id = Column(Integer, ForeignKey('companies.id'))
    cheat_type = Column(Integer)  # Set when cheating is detected
    cheat_date = Column(DateTime) # Set when cheating is detected

    @classmethod
    def get_or_create(cls, session, defaults=None, **kwargs):
        defaults = defaults or {}
        user = cls.find_by_ifv(session, **kwargs) or cls.find_by_ifa(session, **kwargs)

        if not user:
            params = { k : v for k, v in kwargs.iteritems() if not isinstance(v, ClauseElement) }
            params.update(defaults)
            user = cls(**params)
            session.add(user)

        return user

    @classmethod
    def find_by_ifv(cls, session, **kwargs):
        user = cls.get(session, ifv = kwargs['ifv'])
        if user and user.ifa != kwargs['ifa']:
            user.ifa = kwargs['ifa']

        return user

    @classmethod
    def find_by_ifa(cls, session, **kwargs):
        user = cls.get(session, ifa = kwargs['ifa'])
        if user and user.ifv != kwargs['ifv']:
            user.ifv = kwargs['ifv']

        return user

    def set_cheat(self, cheat_type, cheat_date):
        self.cheat_type = self.cheat_type or cheat_type
        self.cheat_date = self.cheat_date or cheat_date


class IOSTransaction(DBTableMixin, Base):
    __tablename__ = 'ios_transactions'

    id             = Column(Integer, primary_key = True)
    company_id     = Column(Integer, ForeignKey('companies.id'))
    game_id        = Column(Integer, ForeignKey('games.id'))
    user_id        = Column(Integer, ForeignKey('users.id'))
    created_on     = Column(DateTime) # Server TS
    xact_id        = Column(String)   # Xact ID from client, for search
    uuid           = Column(String)   # Xact UUID from client library
    client_json    = Column(String)   # Raw JSON from client
    apple_json     = Column(String)   # Raw JSON from apple
    apple_status   = Column(Integer)  # Status from apple
    local_status   = Column(Integer)  # Derived status

    UniqueConstraint('xact_id', 'game_id', name='unq_ios_transactions')

    apple_url = {
        'test' : 'https://sandbox.itunes.apple.com/verifyReceipt',
        'prod' : 'https://buy.itunes.apple.com/verifyReceipt',
    }

    timeout = 1.0

    def apple_api(self, url, receipt):
        """
            The Apple API returns something that looks kinda like this:
            {
                'status': 0,
                'receipt': {
                    'original_transaction_id' : '1000000003043743',
                    'bvrs'                    : '1.0',
                    'quantity'                : '1',
                    'original_purchase_date'  : '2013-08-30 15:16:17 Etc/GMT',
                    'purchase_date'           : '2013-08-30 15:16:17 Etc/GMT',
                    'bid'                     : 'some.bundle.id',
                    'item_id'                 : '532432566',
                    'product_id'              : 'someproduct3',
                    'transaction_id'          : '1000000003043743'
                }
            }
        """
        if os.environ.get('OFFLINE', None):
            raise OfflineError()

        data = json.dumps({ 'receipt-data' : receipt })
        req  = requests.post(url, data = data, timeout = self.timeout, verify = False, stream = False)

        return req

    def verify(self, session, user):
        """
            There are generally four cases where an IAP might be considered invalid.
            1. Apple says the receipt is invalid.
            2. Apple says the receipt is for a different bundle than it was reported under
            3. It's a valid IAP for your bundle, but it was for a different user.
            4. It's a valid IAP for your bundle and on the correct user, but they've used it more than once.
        """

        apple_json  = None
        client_json = None
        new_info    = self.local_status == None

        # First, catch the case of a different user passing in a transaction
        # This is exceedingly common
        if self.user_id != user.id:
            user.set_cheat(Status.INVALID_USER, now())
            return

        if self.game_id != user.game_id:
            user.set_cheat(Status.INVALID_GAME, now())
            return

        # Preexisting IAPs for the same user
        for other_xact in self.get_all(session, xact_id = self.xact_id):
            if other_xact.uuid != self.uuid and other_xact.apple_json:
                self.apple_status = other_xact.apple_status
                self.apple_json = other_xact.apple_json
                self.local_status = Status.DUPLICATE_IAP
                user.set_cheat(self.local_status, now())
                return

        if self.apple_status not in (0, 21007, 21008):
            # We have never gotten a valid response from Apple about this
            # So verify it with Apple
            client_json = json.loads(self.client_json)

            ## Try production
            req = self.apple_api('https://buy.itunes.apple.com/verifyReceipt', client_json['receipt'])
            if req.status_code != 200:
                return

            apple_json = req.json()

            if apple_json['status'] in (21007, 21008):
                # Ok, try the other
                req = self.apple_api('https://sandbox.itunes.apple.com/verifyReceipt', client_json['receipt'])
                if req.status_code != 200:
                    return

                apple_json = req.json()

            self.apple_status = apple_json['status']
            self.apple_json = json.dumps(apple_json)
            new_info = True

        apple_json = apple_json or json.loads(self.apple_json)
        client_json = client_json or json.loads(self.client_json)

        if apple_json['status'] != 0:
            self.local_status = Status.INVALID_RECEIPT
            user.set_cheat(self.local_status, now())

        elif apple_json['receipt']['bid'] != client_json['bid']:
            self.local_status = Status.INVALID_BUNDLE
            user.set_cheat(self.local_status, now())

        else:
            self.local_status = Status.VALID

class Status(object):
    VALID           = 0
    INVALID_USER    = 1
    INVALID_GAME    = 2
    INVALID_BUNDLE  = 3
    INVALID_RECEIPT = 4
    DUPLICATE_IAP   = 5

if __name__ == '__main__':
    Base.metadata.create_all(get_engine())
