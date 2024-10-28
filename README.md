> I stopped playing long time ago as the game sucks now. Archived. Enjoy the bot if you can.

`snail/proxy.py` handles mitmproxy startup/shutdown
`snail/client.py` implements GraphQL operations

## Configuration

Create `owner.conf` with your wallet address

```
$ cat owner.conf
0xbadbadbadbadbadbadbadbadbadbadbadbadbad0
```

Create `pkey.conf` with your private key (hex string, as expored from MetaMask)

```
$ cat pkey.conf
badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbad0
```

Configure an telegram bot to receive notifications, go to https://core.telegram.org/bots#6-botfather for more details on how-to
You need to provide bot token_ID and chat__ID
```
--notify token_ID chat_ID
```

## Quickstart

```
$ pip install -r requirements.txt
$ python --help
$ python main.py --notify token_ID chat_ID bot [xyz]

INFO:__main__:starting proxy
INFO:__main__:proxy ready on http://127.0.0.1:50930
https://www.snailtrail.art/snails/2206/snail 1.55
https://www.snailtrail.art/snails/3941/snail 1.9 2022-06-22 12:21:02
https://www.snailtrail.art/snails/4258/snail 1.9 2022-06-25 19:35:49
https://www.snailtrail.art/snails/1616/snail 1.979 2022-06-28 11:12:32
https://www.snailtrail.art/snails/6539/snail 2.0 2022-06-29 14:18:39
https://www.snailtrail.art/snails/3718/snail 1.85 2022-07-02 10:29:02
```

## Errors 403

api.snailtrail.art (the GraphQL endpoint) is behind cloudflare and it probably has firewall rules set up based on [bot score](https://developers.cloudflare.com/bots/concepts/bot-score).

Python requests, curl and others are always blocked. Public cloud services (such as AWS and OCI) are always blocked (even if using the browser).

Weirdly [mitmproxy](https://mitmproxy.org/) and [burp](https://portswigger.net/burp) seem to have lower bot score than python requests directly, so they are less likely to be blocked (might still be due to other factors).

Default bot implementation starts a builtin mitmproxy instance.  
If external instance is already running (of another mitmproxy, burp or another tool), it can be passed via `--proxy IP:PORT`.

Another option is using the `browserproxy`. This sets up a local forward proxy via browser (Chromium) itself, which also has low bot score.

### browserproxy

This sets up a local forward proxy via browser (Chromium) itself.

To set it up, install Chromium and [chromiumdriver](https://chromedriver.chromium.org/). Then install the script requirements.

```
cd browserproxy
pip install -r requirements.txt
```

Now start `main.py` (use `-h` for more options) and leave it running.

When starting the bot, make sure to set `--proxy ''` (needs to be empty so it does not start builtin mitmproxy) and `--graphql-endpoint http://127.0.0.1:8888/graphql/`.
