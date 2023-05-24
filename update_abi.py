#!/usr/bin/env python -u

import requests
import re
import json5
import json


def main():
    r = requests.get('https://www.snailtrail.art/')
    r.raise_for_status()
    script = re.findall(r'<script src="main\.(.*?)\.js" type="module">', r.text)[0]
    script = f'https://www.snailtrail.art/main.{script}.js'
    print(script)
    r = requests.get(script)
    r.raise_for_status()
    script_data = r.text
    contracts = re.findall(r'contractAddresses:({.*?})', script_data)[0]
    contracts = json5.loads(contracts)
    print(script_data)


if __name__ == '__main__':
    main()
