# generated automatically from https://www.snailtrail.art/main.44a30b30721e5995.js - DO NOT MODIFY

CONTRACT = '0x5a15Bdcf9a3A8e799fa4381E666466a516F2d9C8'

ABI = [
    {
        'inputs': [
            {'internalType': 'string', 'name': 'name', 'type': 'string'},
            {'internalType': 'string', 'name': 'symbol', 'type': 'string'},
            {'internalType': 'address', 'name': 'owner', 'type': 'address'},
        ],
        'stateMutability': 'nonpayable',
        'type': 'constructor',
    },
    {
        'anonymous': False,
        'inputs': [
            {'indexed': True, 'internalType': 'address', 'name': 'owner', 'type': 'address'},
            {'indexed': True, 'internalType': 'address', 'name': 'spender', 'type': 'address'},
            {'indexed': False, 'internalType': 'uint256', 'name': 'value', 'type': 'uint256'},
        ],
        'name': 'Approval',
        'type': 'event',
    },
    {
        'anonymous': False,
        'inputs': [
            {'indexed': True, 'internalType': 'address', 'name': 'previousOwner', 'type': 'address'},
            {'indexed': True, 'internalType': 'address', 'name': 'newOwner', 'type': 'address'},
        ],
        'name': 'OwnershipTransferred',
        'type': 'event',
    },
    {
        'anonymous': False,
        'inputs': [{'indexed': False, 'internalType': 'address', 'name': 'account', 'type': 'address'}],
        'name': 'Paused',
        'type': 'event',
    },
    {
        'anonymous': False,
        'inputs': [
            {'indexed': True, 'internalType': 'address', 'name': 'from', 'type': 'address'},
            {'indexed': True, 'internalType': 'address', 'name': 'to', 'type': 'address'},
            {'indexed': False, 'internalType': 'uint256', 'name': 'value', 'type': 'uint256'},
        ],
        'name': 'Transfer',
        'type': 'event',
    },
    {
        'anonymous': False,
        'inputs': [{'indexed': False, 'internalType': 'address', 'name': 'account', 'type': 'address'}],
        'name': 'Unpaused',
        'type': 'event',
    },
    {
        'inputs': [
            {'internalType': 'address', 'name': 'owner', 'type': 'address'},
            {'internalType': 'address', 'name': 'spender', 'type': 'address'},
        ],
        'name': 'allowance',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'address', 'name': 'spender', 'type': 'address'},
            {'internalType': 'uint256', 'name': 'amount', 'type': 'uint256'},
        ],
        'name': 'approve',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'address', 'name': 'account', 'type': 'address'}],
        'name': 'balanceOf',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': 'amount', 'type': 'uint256'}],
        'name': 'burn',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'address', 'name': 'account', 'type': 'address'},
            {'internalType': 'uint256', 'name': 'amount', 'type': 'uint256'},
        ],
        'name': 'burnFrom',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'decimals',
        'outputs': [{'internalType': 'uint8', 'name': '', 'type': 'uint8'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'address', 'name': 'spender', 'type': 'address'},
            {'internalType': 'uint256', 'name': 'subtractedValue', 'type': 'uint256'},
        ],
        'name': 'decreaseAllowance',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'address', 'name': 'spender', 'type': 'address'},
            {'internalType': 'uint256', 'name': 'addedValue', 'type': 'uint256'},
        ],
        'name': 'increaseAllowance',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'name',
        'outputs': [{'internalType': 'string', 'name': '', 'type': 'string'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'owner',
        'outputs': [{'internalType': 'address', 'name': '', 'type': 'address'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {'inputs': [], 'name': 'pause', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
    {
        'inputs': [],
        'name': 'paused',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {'inputs': [], 'name': 'renounceOwnership', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
    {
        'inputs': [],
        'name': 'symbol',
        'outputs': [{'internalType': 'string', 'name': '', 'type': 'string'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'totalSupply',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'address', 'name': 'recipient', 'type': 'address'},
            {'internalType': 'uint256', 'name': 'amount', 'type': 'uint256'},
        ],
        'name': 'transfer',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'address', 'name': 'sender', 'type': 'address'},
            {'internalType': 'address', 'name': 'recipient', 'type': 'address'},
            {'internalType': 'uint256', 'name': 'amount', 'type': 'uint256'},
        ],
        'name': 'transferFrom',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'address', 'name': 'newOwner', 'type': 'address'}],
        'name': 'transferOwnership',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {'inputs': [], 'name': 'unpause', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
]
