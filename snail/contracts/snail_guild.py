# generated automatically from https://www.snailtrail.art/main.d3905bf907602c39.js - DO NOT MODIFY

CONTRACT = '0x405eda4e38d863B18662250034C252D463d3a707'

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
            {'indexed': True, 'internalType': 'address', 'name': 'previousOwner', 'type': 'address'},
            {'indexed': True, 'internalType': 'address', 'name': 'newOwner', 'type': 'address'},
        ],
        'name': 'OwnershipTransferred',
        'type': 'event',
    },
    {
        'anonymous': False,
        'inputs': [
            {'indexed': False, 'internalType': 'uint256', 'name': 'stakeOrderID', 'type': 'uint256'},
            {'indexed': False, 'internalType': 'address', 'name': 'owner', 'type': 'address'},
        ],
        'name': 'SnailsStaked',
        'type': 'event',
    },
    {
        'anonymous': False,
        'inputs': [
            {'indexed': False, 'internalType': 'address', 'name': 'owner', 'type': 'address'},
            {'indexed': False, 'internalType': 'uint256[]', 'name': 'tokenIDs', 'type': 'uint256[]'},
        ],
        'name': 'SnailsUnstaked',
        'type': 'event',
    },
    {
        'inputs': [
            {'internalType': 'address', 'name': 'nftAddress', 'type': 'address'},
            {'internalType': 'address', 'name': 'tokenAddress', 'type': 'address'},
        ],
        'name': 'initialize',
        'outputs': [],
        'stateMutability': 'nonpayable',
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
        'inputs': [
            {
                'components': [
                    {'internalType': 'uint256', 'name': 'stakeOrderID', 'type': 'uint256'},
                    {'internalType': 'address', 'name': 'owner', 'type': 'address'},
                    {'internalType': 'uint256[]', 'name': 'tokenIDs', 'type': 'uint256[]'},
                    {'internalType': 'uint256', 'name': 'timeout', 'type': 'uint256'},
                    {'internalType': 'uint256', 'name': 'salt', 'type': 'uint256'},
                ],
                'internalType': 'struct SnailTrailGuild.StakeModel',
                'name': 'stakeModel',
                'type': 'tuple',
            },
            {'internalType': 'bytes', 'name': 'sig', 'type': 'bytes'},
        ],
        'name': 'stakeSnails',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'name': 'stakedSnailsOwner',
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
        'inputs': [{'internalType': 'uint256[]', 'name': 'tokenIDs', 'type': 'uint256[]'}],
        'name': 'unstakeSnails',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
]
