import os
import pyutil.sqlutil
from pyutil.decorators import *

__all__ = [
    'DBTableMixin',
    'get_session',
    'default_session',
    'get_engine',
    'get_config',
]

DBTableMixin    = pyutil.sqlutil.DBTableMixin
get_session     = pyutil.sqlutil.get_session
default_session = pyutil.sqlutil.default_session
get_engine      = pyutil.sqlutil.get_engine

@memoize()
def get_config():
    return pyutil.util.load_json_paths(
        os.path.join(os.environ.get('IAP_SERVICE_CONFIG', '/etc'), 'db_info'),
        "iap_svc_cfg",
        "~/.iap_svc_cfg",
    )

pyutil.sqlutil.set_config(get_config())
