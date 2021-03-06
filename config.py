from dotenv import load_dotenv
import os
import telepot
import urllib3
from uuid import uuid4
import logging
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
        self.db_conn = "mysql://willdrug:%s@willdrug.mysql.pythonanywhere-services.com/willdrug$cmb?charset=utf8" % os.environ.get('SQLPWD')
        self.webhook_addr = f"https://willdrug.pythonanywhere.com/{path}"
        self.path = path
        self.demiurge = 391834810
        self.bullshit_threshhold = 20
        self.bullshit_punish = 86400
        self.poke_remind = 43200
        self.poke_resend = 86400
        init_proxy()

class Test:
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        project_folder = os.path.abspath('')  # adjust as appropriate
        load_dotenv(os.path.join(project_folder, '.env'))
        self.db_conn = "sqlite:///test.db"
        self.webhook_addr = 'http://'
        self.path = 'bot'
        self.demiurge = 391834810
        self.bullshit_threshhold = 20
        self.bullshit_punish = 2
        self.poke_remind = 1
        self.poke_resend = 5


config = Production()
