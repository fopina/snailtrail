import subprocess
import time

import requests


def _free_port():
    import socket

    sock = socket.socket()
    sock.bind(('', 0))
    p = sock.getsockname()[1]
    sock.close()
    return p


class Proxy:
    def __init__(self, binary, quiet=True, port=None, upstream_proxy=None):
        self._binary = binary
        self._quiet = quiet
        self._port = port if port else _free_port()
        self._upstream = upstream_proxy
        self._process = None

    def url(self):
        return f'http://127.0.0.1:{self._port}'

    def start(self, wait_for_ready=True):
        if not self._binary.is_file():
            raise Exception(
                'could not find gotls binary, build it (from gotlsproxy) or download binaries from https://github.com/fopina/gotlsproxy/releases/latest',
                self._binary,
            )
        args = [self._binary, '--bind', f':{self._port}']
        # FIXME: implement upstream proxy
        if self._upstream:
            args.extend(['--mode', f'upstream:{self._upstream}'])
        args.append('https://api.snailtrail.art/graphql/')
        args.extend([
            '-ja3', '771,4865-4867-4866-49195-49199-52393-52392-49196-49200-49162-49161-49171-49172-156-157-47-53-10,0-23-65281-10-11-35-16-5-34-51-43-13-45-28-65037,29-23-24-25-256-257,0',
            '-ua', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
        ])
        self._process = subprocess.Popen(args)
        if wait_for_ready:
            for _ in range(50):
                try:
                    requests.get(self.url())
                    break
                except requests.exceptions.ConnectionError:
                    time.sleep(0.1)
            else:
                raise Exception('proxy not starting')

    def stop(self):
        self._process.terminate()
