from selenium import webdriver
from pathlib import Path
from selenium.webdriver.common.by import By
import json


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

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger(__name__)

    logger.info("logging in")
    driver = MyDriver(docker=False)
    driver.implicitly_wait(20)


    driver.get("https://api.snailtrail.art/graphql/")
    el = driver.find_element(By.TAG_NAME, "textarea")
    logger.info('ready')
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class MyServer(BaseHTTPRequestHandler):
        def do_POST(self):
            content_len = int(self.headers.get('content-length', 0))
            post_body = json.dumps(self.rfile.read(content_len).decode())
            try:
                data = driver.execute_script(
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
                    return [r.status, await r.text()];
                    '''
                )
                self.send_response(data[0])
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(bytes(data[1], "utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-type", "text/plan")
                self.end_headers()
                self.wfile.write(bytes(str(e), "utf-8"))
                raise

    webServer = HTTPServer(('', 8888), MyServer)
    print("Server started http://%s:%s" % ('', 8888))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")
