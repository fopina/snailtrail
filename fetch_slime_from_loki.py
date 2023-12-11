import requests
import argparse
import re


def main():
    p = argparse.ArgumentParser()
    p.add_argument('hostname')
    p.add_argument('username')
    p.add_argument('password')
    p.add_argument('service_name')
    args = p.parse_args()

    patt = re.compile(r'for Treasury Run, reward (.*?)"')

    end = None
    pend = None
    total = 0
    first = None
    while True:
        print('Total', total, 'Next', end)
        r = requests.post(
            f'https://{args.hostname}/loki/api/v1/query_range',
            auth=(args.username, args.password),
            data={
                'query': f'{{source="docker",service="{args.service_name}"}} |= "reward"',
                'limit': 5000,
                'end': end,
                'since': '10d',
            }
        )
        r.raise_for_status()
        for e in r.json()['data']['result']:
            for e2 in e['values']:
                ts = int(e2[0])
                if pend and ts >= pend:
                    continue
                if not first:
                    first = ts
                    print('FIRST', first)
                m = patt.findall(e2[1])
                if not m:
                    print('WHAT', e2)
                    continue
                total += float(m[0])
                end = ts
        if pend == end:
            break
        pend = end


if __name__ == '__main__':
    main()
