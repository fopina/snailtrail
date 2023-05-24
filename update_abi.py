#!/usr/bin/env python -u

import requests
import re
import json5

EXPECTED_CONTRACTS = 12


def assert_equal(expected, got):
    if expected != got:
        raise AssertionError(f'Expected {expected}, got {got}')


class Parser:
    def fetch_script(self):
        r = requests.get('https://www.snailtrail.art/')
        r.raise_for_status()
        script = re.findall(r'<script src="main\.(.*?)\.js" type="module">', r.text)[0]
        self.script_url = f'https://www.snailtrail.art/main.{script}.js'
        r = requests.get(self.script_url)
        r.raise_for_status()
        self.script_data = r.text

    def extract_contracts(self):
        contracts = re.findall(r'contractAddresses:({.*?})', self.script_data)[0]
        self.contracts = json5.loads(contracts)
        assert_equal(EXPECTED_CONTRACTS, len(self.contracts))

    def extract_abi(self):
        first_l = None
        for l in re.findall(r'(\bextends \w+?\.ContractFactory)\b', self.script_data):
            if first_l is None:
                first_l = l
            else:
                assert_equal(first_l, l)

        start = 0
        abis = []

        while True:
            i = self.script_data.find(first_l, start)
            if i < 0:
                break
            start = i + 50

            while self.script_data[i] != ';':
                i -= 1
            factory = i + 1
            assert_equal('let ', self.script_data[factory : factory + 4])

            i -= 1
            while self.script_data[i] != ';':
                i -= 1
            abi = i + 1
            assert_equal('const ', self.script_data[abi : abi + 6])

            # find factory variable
            e = self.script_data.find('=', factory)
            var_factory = self.script_data[factory + 4 : e]

            # find abi variable
            e = self.script_data.find('=', abi)
            var_abi = self.script_data[abi + 6 : e]

            # extract ABI definition
            si = i = self.script_data.find('[', abi) + 1
            bc = 1
            while bc > 0:
                if self.script_data[i] == '[':
                    bc += 1
                elif self.script_data[i] == ']':
                    bc -= 1
                i += 1
            abi_code = self.script_data[si - 1 : i]
            abi_code = abi_code.replace('!1', 'false')
            abi_code = abi_code.replace('!0', 'true')
            abi_definition = json5.loads(abi_code)

            abis.append((var_factory, var_abi, abi_definition))

        # FIXME: find missing contract
        assert_equal(EXPECTED_CONTRACTS - 1, len(abis))

    def run(self):
        self.fetch_script()
        self.extract_contracts()
        self.extract_abi()


def main():
    Parser().run()


if __name__ == '__main__':
    main()
