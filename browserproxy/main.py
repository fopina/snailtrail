#!/usr/bin/env python

import argparse
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class MyDriver(webdriver.Chrome):
    def __init__(self, executable_path="chromedriver", docker=False, **kwargs):
        options = webdriver.ChromeOptions()
        if Path("/Applications/Chromium.app/Contents/MacOS/Chromium").exists():
            # for dev environment
            options.binary_location = "/Applications/Chromium.app/Contents/MacOS/Chromium"
        # hide selenium! all possible flags found online :shrug:
        if docker:
            options.headless = True
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("start-maximized")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-blink-features=AutomationControlled")
        super().__init__(executable_path=executable_path, options=options, **kwargs)
        self.execute_cdp_cmd(
            "Network.setUserAgentOverride",
            {"userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:102.0) Gecko/20100101 Firefox/102.0"},
        )


class MyServer(BaseHTTPRequestHandler):
    def do_POST(self):
        content_len = int(self.headers.get('content-length', 0))
        post_body = json.dumps(self.rfile.read(content_len).decode())
        try:
            data = self.server.driver.execute_script(
                f'''
                const r = await fetch(
                    "https://api.snailtrail.art/graphql/",
                    {{
                        method: 'POST',
                        headers: {{
                            'Accept': 'application/json',
                            'Content-Type': 'application/json'
                        }},
                    body: {post_body}
                    }}
                );
                return [r.status, await r.text(), ...r.headers];
                '''
            )
            self.send_response(data[0])
            for h in data[2:]:
                if h[0].lower() == 'content-encoding':
                    continue
                self.send_header(h[0], h[1])
            self.end_headers()
            self.wfile.write(bytes(data[1], "utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "text/plan")
            self.end_headers()
            self.wfile.write(bytes(str(e), "utf-8"))
            raise


def build_parser():
    p = argparse.ArgumentParser()
    p.add_argument('--endpoint', type=str, default='https://api.snailtrail.art/graphql/', help='GraphQL endpoint')
    p.add_argument(
        '--show',
        action='store_true',
        help='Show browser',
    )
    p.add_argument('-b', '--bind-address', default='127.0.0.1', help='Server listening interface')
    p.add_argument('-p', '--port', default=8888, help='Server listening port')
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    logger.info("launching browser")
    driver = MyDriver(docker=not args.show)
    driver.implicitly_wait(20)

    driver.get(args.endpoint)
    # random element to wait for page load
    driver.find_element(By.TAG_NAME, "textarea")
    logger.info('starting httpd')

    webServer = HTTPServer((args.bind_address, args.port), MyServer)
    webServer.driver = driver
    print(f'Server started http://{args.bind_address}:{args.port}')

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")


if __name__ == '__main__':
    main()
