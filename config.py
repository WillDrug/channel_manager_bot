from dotenv import load_dotenv
import os
import telepot
import urllib3
from uuid import uuid4
path = uuid4()


def init_proxy():
    # ----Pythonanywhere specific part--------
    proxy_url = "http://proxy.server:3128"
    telepot.api._pools = {
        'default': urllib3.ProxyManager(proxy_url=proxy_url, num_pools=3, maxsize=10, retries=False, timeout=30),
    }
    telepot.api._onetime_pool_spec = (
        urllib3.ProxyManager, dict(proxy_url=proxy_url, num_pools=1, maxsize=1, retries=False, timeout=30))
    # ----------------------------------------

class Production:
    def __init__(self):
        project_folder = os.path.expanduser('~/channel_manager_bot')  # adjust as appropriate
        load_dotenv(os.path.join(project_folder, '.env'))

        self.db_conn = "mysql://willdrug:%s@willdrug.mysql.pythonanywhere-services.com/willdrug$cmb" % os.environ.get('SQLPWD')
        self.webhook_addr = f"https://willdrug.pythonanywhere.com/{path}"
        self.path = path
        init_proxy()

class Test:
    def __init__(self):
        project_folder = os.path.abspath('')  # adjust as appropriate
        load_dotenv(os.path.join(project_folder, '.env'))
        self.db_conn = "sqlite:///test.db"
        self.webhook_addr = ''
        self.path = ''


config = Production()