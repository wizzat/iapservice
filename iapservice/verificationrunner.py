from iapservice.util import default_session
from model import IOSTransaction

def run():
    session = default_session()
    for xact in IOSTransaction.get_all(local_status = None):
        try:
            user = User.get(xact.user_id)
            xact.verify(session, user)
            session.add(xact)
            session.add(user)
            session.commit()
        except Exception:
            # Yeah, ok
            pass

    if len(IOSTransaction.get_all(local_status = None)) > 10:
        raise ProcessingBehindError()

if __name__ == '__main__':
    run()
