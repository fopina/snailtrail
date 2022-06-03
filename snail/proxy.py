from mitmproxy.tools import main
from multiprocessing import Process
import requests
import time

requests.packages.urllib3.disable_warnings()


def _free_port():
        import socket
        sock = socket.socket()
        sock.bind(('', 0))
        p = sock.getsockname()[1]
        sock.close()
        return p


class Proxy():
    def __init__(self, quiet=True, port=None, upstream_proxy=None):
        self._quiet = quiet
        self._port = port if port else _free_port()
        self._upstream = upstream_proxy
        self._process = None
    
    def url(self):
        return f'http://127.0.0.1:{self._port}'

    def start(self, wait_for_ready=True):
        args = ['--listen-port', str(self._port)]
        if self._quiet:
            args.append('-q')
        if self._upstream:
            args.extend(['--mode', f'upstream:{self._upstream}'])
        self._process = Process(target=main.mitmdump, args=(args,), daemon=True)
        self._process.start()
        if wait_for_ready:
            for _ in range(50):
                try:
                    requests.get('http://1.1.1.1', proxies={'https': self.url()}, verify=False)
                    break
                except requests.exceptions.ProxyError:
                    time.sleep(0.1)
            else:
                raise Exception('proxy not starting')
    
    def stop(self):
        self._process.terminate()
