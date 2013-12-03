from iapservice.model import *
from iapservice.util import *
from iapservice.server import VerifyRequest
from pyutil.testutil import *
from pyutil.dateutil import *
import unittest, json, uuid, requests, os

class TestVerification(unittest.TestCase):
    """
    In order to run this test case, you need to create two files:
    ios_developer_secret - this contains your iOS developer secret for IAP verification.
    valid_iap - this contains a JSON object.  It minimally looks something like this:

    """
    def test_creates_user(self):
        VerifyRequest.record_data(self.valid_iap)
        user = User.get(ifa = self.valid_iap['ifa'], ifv = self.valid_iap['ifv'])
        self.assertEqual(user.game_id, self.game.id)
        self.assertEqual(user.company_id, self.company.id)

    def test_valid_iap(self):
        VerifyRequest.record_data(self.valid_iap)
        user = User.get(ifa = self.valid_iap['ifa'])
        xact = IOSTransaction.get(xact_id = self.valid_iap['xact_id'])

        self.assertEqual(xact.local_status, 0)
        self.assertEqual(user.cheat_date, None)
        self.assertEqual(user.cheat_type, None)

    def test_invalid_iap(self):
        invalid_iap = dict(self.valid_iap)
        invalid_iap['ifa'] = str(uuid.uuid4())
        invalid_iap['ifv'] = str(uuid.uuid4())
        invalid_iap['xact_id'] = str(uuid.uuid4())
        invalid_iap['receipt'] = 'a' + invalid_iap['receipt'][1:]

        VerifyRequest.record_data(invalid_iap)

        user = User.get(ifa = invalid_iap['ifa'])
        self.assertEqual(user.cheat_date, now())
        self.assertEqual(user.cheat_type, Status.INVALID_RECEIPT)

        xact = IOSTransaction.get(xact_id = invalid_iap['xact_id'])
        self.assertEqual(xact.apple_status, 21002)
        self.assertEqual(xact.local_status, Status.INVALID_RECEIPT)

    def test_valid_iap_with_different_user_is_invalid(self):
        VerifyRequest.record_data(self.valid_iap)

        inv_req = dict(self.valid_iap)
        inv_req['ifa'] = str(uuid.uuid4())
        inv_req['ifv'] = str(uuid.uuid4())

        VerifyRequest.record_data(inv_req)

        valid_user = User.get(ifv = self.valid_iap['ifv'])
        invalid_user = User.get(ifv = inv_req['ifv'])

        xact = IOSTransaction.get(xact_id = self.valid_iap['xact_id'])
        self.assertEqual(xact.local_status, Status.VALID)
        self.assertEqual(xact.user_id, valid_user.id)

        self.assertNotEqual(valid_user.id, invalid_user.id)
        self.assertEqual(valid_user.cheat_type, None)
        self.assertEqual(invalid_user.cheat_type, Status.INVALID_USER)

    def test_valid_iap_with_different_bundle_is_invalid(self):
        inv_req = dict(self.valid_iap)
        inv_req['ifa'] = str(uuid.uuid4())
        inv_req['ifv'] = str(uuid.uuid4())
        inv_req['bid'] = 'something altogether different entirely'

        VerifyRequest.record_data(inv_req)
        user = User.get(ifv = inv_req['ifv'])
        xact = IOSTransaction.get(xact_id = inv_req['xact_id'])

        self.assertEqual(user.cheat_type, Status.INVALID_BUNDLE)
        self.assertEqual(user.cheat_date, now())
        self.assertEqual(xact.local_status, Status.INVALID_BUNDLE)

    def test_apple_service_down(self):
        user = User.get_or_create(self.session,
            ifa        = 'abc',
            ifv        = 'def',
            game_id    = self.game.id,
            company_id = self.game.company_id,
        )
        self.session.commit()

        xact = IOSTransaction(
            company_id  = self.game.company_id,
            game_id     = self.game.id,
            xact_id     = 'abc',
            user_id     = user.id,
            client_json = json.dumps({'ifa' : 'abc', 'ifv' : 'def', 'receipt' : 'abc' }),
        )
        self.session.add(xact)
        self.session.commit()

        xact.timeout = 0.0001
        self.assertRaises(requests.Timeout, lambda: xact.verify(self.session, user))
        self.session.commit()
        self.session.close()

    def test_duplicate_iaps_for_same_user(self):
        VerifyRequest.record_data(self.valid_iap)
        valid_user = User.get(ifv = self.valid_iap['ifv'])
        valid_xact = IOSTransaction.get(uuid = self.valid_iap['uuid'])

        self.assertEqual(valid_user.cheat_date, None)
        self.assertEqual(valid_xact.local_status, Status.VALID)

        inv_req = dict(self.valid_iap)
        inv_req['uuid'] = str(uuid.uuid4())

        set_now(None)
        set_now(now())

        VerifyRequest.record_data(inv_req)
        default_session().commit() # This refreshes all the SQLAlchemy objects

        invalid_user = User.get(ifv = inv_req['ifv'])
        invalid_xact = IOSTransaction.get(uuid = inv_req['uuid'])

        self.assertEqual(invalid_xact.local_status, Status.DUPLICATE_IAP)

        self.assertEqual(valid_user.id, invalid_user.id)
        self.assertEqual(invalid_user.cheat_date, now())

    def test_true_duplicate_iap(self):
        VerifyRequest.record_data(self.valid_iap)
        VerifyRequest.record_data(self.valid_iap)

        user  = User.get(ifv = self.valid_iap['ifv'])
        xact  = IOSTransaction.get(xact_id = self.valid_iap['xact_id'])
        xacts = IOSTransaction.get_all(xact_id = self.valid_iap['xact_id'])

        self.assertEqual(len(xacts), 1)
        self.assertEqual(user.cheat_date, None)
        self.assertEqual(xact.local_status, Status.VALID)

    valid_iap = None
    def setUp(self):
        super(TestVerification, self).setUp()
        if not self.valid_iap:
            local_path = os.path.join(os.environ.get('IAP_SERVICE_CONFIG', '/etc'), 'valid_iap')

            with open(local_path, "r") as fp:
                self.valid_iap = json.load(fp)

        # Grab a separate session than the default session
        # So that we know that persistence is working
        self.session = get_session()

        self.session.query(IOSTransaction).delete()
        self.session.query(IOSPackage).delete()
        self.session.query(User).delete()
        self.session.query(Game).delete()
        self.session.query(Company).delete()
        self.session.commit()

        set_now(None)
        set_now(now())

        self.company = Company.get_or_create(self.session, name = 'Some Company')
        self.session.commit()

        self.game = Game.get_or_create(self.session,
            name        = 'Some Game',
            game_secret = 'a secret',
            company_id  = self.company.id,
        )
        self.session.commit()


if __name__ == '__main__':
    unittest.main()
