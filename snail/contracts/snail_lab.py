# generated automatically from https://www.snailtrail.art/main.44a30b30721e5995.js - DO NOT MODIFY

CONTRACT = '0x0767F23Cb69AC937d44926d0950D240c777d8F78'

ABI = [
    {
        'anonymous': False,
        'inputs': [{'indexed': False, 'internalType': 'uint8', 'name': 'version', 'type': 'uint8'}],
        'name': 'Initialized',
        'type': 'event',
    },
    {
        'anonymous': False,
        'inputs': [
            {'indexed': False, 'internalType': 'address', 'name': 'owner', 'type': 'address'},
            {'indexed': False, 'internalType': 'uint256', 'name': 'orderID', 'type': 'uint256'},
        ],
        'name': 'LabOrderExecuted',
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
    {'stateMutability': 'payable', 'type': 'fallback'},
    {
        'inputs': [],
        'name': 'graveyardContractAddress',
        'outputs': [{'internalType': 'address', 'name': '', 'type': 'address'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'address', 'name': 'nftAddress', 'type': 'address'},
            {'internalType': 'address', 'name': 'tokenAddress', 'type': 'address'},
            {'internalType': 'address', 'name': '_graveyardContractAddress', 'type': 'address'},
        ],
        'name': 'initialize',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'isLabEnabled',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
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
    {'inputs': [], 'name': 'renounceOwnership', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
    {
        'inputs': [{'internalType': 'address', 'name': 'newAddress', 'type': 'address'}],
        'name': 'setSigner',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'signerPublicAddress',
        'outputs': [{'internalType': 'address', 'name': '', 'type': 'address'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'address', 'name': 'newOwner', 'type': 'address'}],
        'name': 'transferOwnership',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [
            {
                'components': [
                    {'internalType': 'uint256', 'name': 'orderID', 'type': 'uint256'},
                    {'internalType': 'uint256', 'name': 'size', 'type': 'uint256'},
                    {'internalType': 'uint256[]', 'name': 'tokenIDs', 'type': 'uint256[]'},
                    {'internalType': 'address', 'name': 'owner', 'type': 'address'},
                    {'internalType': 'uint256', 'name': 'fee', 'type': 'uint256'},
                    {'internalType': 'uint256', 'name': 'timeout', 'type': 'uint256'},
                    {'internalType': 'uint256', 'name': 'salt', 'type': 'uint256'},
                ],
                'internalType': 'struct SnailTrailLab.LabModel',
                'name': 'labModel',
                'type': 'tuple',
            },
            {'internalType': 'bytes', 'name': 'sig', 'type': 'bytes'},
        ],
        'name': 'useLab',
        'outputs': [],
        'stateMutability': 'payable',
        'type': 'function',
    },
    {'inputs': [], 'name': 'withdraw', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
    {'inputs': [], 'name': 'withdrawBalance', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
    {
        'inputs': [{'internalType': 'contract IERC20', 'name': 'token', 'type': 'address'}],
        'name': 'withdrawErc20',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {'stateMutability': 'payable', 'type': 'receive'},
]
