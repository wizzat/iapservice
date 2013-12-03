from iapservice.model import get_session, Game, Company, User, IOSTransaction
from iapservice.util import *
from pyutil.dateutil import *
import requests, zlib, web, json

__all__ = [
    'VerifyRequest',
]

class VerifyRequest(object):
    invalid_params = [
        'cheat_type',
        'cheat_date',
        'uid',
        'apple_status'
        'apple_bid',
        'apple_bvrs',
        'game_id',
    ]

    def GET(self):
        pass

    def POST(self):
        """
        Expects a JSON object that looks something like this:

        {
            "game_secret" : "a shared secret between you and the server per game",
            "ifa"         : "1ad75bdc85527914459b41f44f3af0ff",
            "ifv"         : "f43adc9fc7548eef59b9314ec88078f6",
            "receipt"     : "8f4c538fb296a31b49bd38360ce49f838f4c538fb296a31b49bd38360ce49f838f4c538fb296a31b49bd38360ce49f838f4c538fb296a31b49bd38360ce49f83==",
            "xact_id"     : "06f5d6cbfd02476834906e83816662f8",
            "bid"         : "some game bundle id",
            "bvrs"        : "1.0",
        }

        Passing along extra data with the transaction is encouraged.  Examples include:
        - device_type
        - device_version
        - os_version
        - level
        - playtime at transaction time

        Data passed that interferes with the internal usage of the verification server will be discarded.
        """

        post_body = urllib.unquote(web.data())

        try:
            # In theory I should check the header for compression.  This costs more, but is more foolproof.
            # Honestly, if your games are making so much money that this is a problem, you can afford to spin
            # up a medium instance instead of a micro.

            post_body = zlib.decompress(post_body)
        except zlib.error:
            pass

        try:
            post_body = post_body.decode("utf-8")
            data = json.loads(post_body)
        except ValueError:
            raise web.BadRequest("invalid json")

        for param in invalid_params:
            if param in data:
                raise web.BadRequest("invalid param " + param)

        try:
            return self.record_data(data)
        except InvalidGameError:
            return web.BadRequest("Invalid Game")

    @classmethod
    def record_data(self, data):
        session = get_session()

        game = Game.get(session, game_secret = data['game_secret'])
        if not game:
            raise InvalidGameError()

        data['game_id'] = game.id
        user = User.get_or_create(session,
            ifa        = data['ifa'],
            ifv        = data['ifv'],
            game_id    = game.id,
            company_id = game.company_id,
        )
        user.created_on = user.created_on or now()
        session.commit()

        xact = IOSTransaction.get_or_create(session,
            company_id  = game.company_id,
            game_id     = game.id,
            xact_id     = data['xact_id'],
            uuid        = data['uuid'],
        )

        xact.created_on  = xact.created_on or now()
        xact.user_id     = xact.user_id or user.id
        xact.client_json = xact.client_json or json.dumps(data)

        session.commit()

        try:
            xact.verify(session, user)
        except requests.Timeout:
            # We'll have to swing back by in the batch runner
            pass

        session.commit()
        session.close()

        return "OK"

if __name__ == '__main__':
    from gevent import wsgi
    urls = (
        '/verify', 'VerifyRequest',
    )

    app = web.application(urls, globals())
    wsgi.WSGIServer(('', 8081), app.wsgifunc()).serve_forever()
