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

## Quickstart

```
$ pip install -r requirements.txt
$ python cli.py

INFO:__main__:starting proxy
INFO:__main__:proxy ready on http://127.0.0.1:50930
https://www.snailtrail.art/snails/2206/snail 1.55
https://www.snailtrail.art/snails/3941/snail 1.9 2022-06-22 12:21:02
https://www.snailtrail.art/snails/4258/snail 1.9 2022-06-25 19:35:49
https://www.snailtrail.art/snails/1616/snail 1.979 2022-06-28 11:12:32
https://www.snailtrail.art/snails/6539/snail 2.0 2022-06-29 14:18:39
https://www.snailtrail.art/snails/3718/snail 1.85 2022-07-02 10:29:02
```
