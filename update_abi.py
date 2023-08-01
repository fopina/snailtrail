#!/usr/bin/env python -u

import requests
import re
import json
import json5
from pathlib import Path
import subprocess
import time

EXPECTED_CONTRACTS = 12
CONTRACT_DIR = Path(__file__).absolute().parent / 'snail' / 'contracts'


def assert_equal(expected, got):
    if expected != got:
        raise AssertionError(f'Expected {expected}, got {got}')


def assert_in(container, member):
    if member not in container:
        raise AssertionError(f'Expected {member} to be in {container}')


def camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


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
        for l in re.findall(r'(\bextends (\w+?)\.ContractFactory)\b', self.script_data):
            if first_l is None:
                first_l = l
            else:
                assert_equal(first_l, l)

        contract_class = first_l[1]
        first_l = None
        for l in re.findall(rf'(\bnew {contract_class}\.Contract)\b', self.script_data):
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

        assert_equal(EXPECTED_CONTRACTS, len(abis))
        self.abis = abis

    def match_abis(self):
        self.abi_with_contract = []
        candidates = {m[0]: m[1] for m in re.findall(r'\{super\(([$_\-\w]+?),"(\w+)"\)', self.script_data)}
        for abi in self.abis:
            assert_in(candidates, abi[0])
            c = candidates[abi[0]]
            assert_in(self.contracts, c)
            self.abi_with_contract.append((abi[2], c))

        assert_equal(EXPECTED_CONTRACTS, len(self.abi_with_contract))

    def update_files(self):
        path = CONTRACT_DIR
        path.mkdir(exist_ok=True)
        header = f'# generated automatically from {self.script_url} - DO NOT MODIFY'
        for abi_definition, contract in self.abi_with_contract:
            camel = camel_to_snake(contract)
            address = self.contracts[contract]
            f = path / f'{camel}.py'
            f.write_text(
                f'''{header}

CONTRACT = '{address}'

ABI = {repr(abi_definition)}
'''
            )

    def _update_contract(self, address, contract):
        r = requests.get(f'https://api.snowtrace.io/api?module=contract&action=getabi&address={address}')
        r.raise_for_status()
        abi_definition = json.loads(r.json()['result'])
        f = CONTRACT_DIR / f'{contract}.py'
        header = f'# generated automatically - DO NOT MODIFY'
        f.write_text(
            f'''{header}

CONTRACT = '{address}'

ABI = {repr(abi_definition)}
'''
        )

    def update_bulk_transfer(self):
        return self._update_contract('0xee5b5376d71d4af51bdc64ca353f51485fa8d6d5', 'bulk_transfer')

    def update_multicall(self):
        return self._update_contract('0xca11bde05977b3631167028862be2a173976ca11', 'multicall')

    def update_traderjoe(self):
        return self._update_contract('0xb4315e873dbcf96ffd0acd8ea43f689d8c20fb30', 'traderjoe')

    def update_init(self):
        path = CONTRACT_DIR
        modules = [f'from . import {l.stem}' for l in path.glob('*.py') if l.stem != '__init__']
        modules.sort()
        header = f'# generated automatically - DO NOT MODIFY'
        (path / '__init__.py').write_text('\n'.join([header, ''] + modules))

    def black_em(self):
        subprocess.check_call(['black', CONTRACT_DIR])

    def run(self):
        self.fetch_script()
        self.extract_contracts()
        self.extract_abi()
        self.match_abis()
        # all contracts matched
        assert_equal(set(), set(self.contracts.keys()) - set(x[1] for x in self.abi_with_contract))
        self.update_files()

        self.update_bulk_transfer()
        time.sleep(5)
        self.update_multicall()
        time.sleep(5)
        self.update_traderjoe()

        self.update_init()
        self.black_em()


def main():
    Parser().run()


if __name__ == '__main__':
    main()
