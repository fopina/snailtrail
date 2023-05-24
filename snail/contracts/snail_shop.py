# generated automatically from https://www.snailtrail.art/main.d3905bf907602c39.js - DO NOT MODIFY

CONTRACT = '0xE00CC7624d4108390369c5837c9D0Ca862CFD345'

ABI = [
    {
        'anonymous': False,
        'inputs': [{'indexed': False, 'internalType': 'uint8', 'name': 'version', 'type': 'uint8'}],
        'name': 'Initialized',
        'type': 'event',
    },
    {
        'anonymous': False,
        'inputs': [{'indexed': False, 'internalType': 'uint256', 'name': 'orderId', 'type': 'uint256'}],
        'name': 'ItemPurchased',
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
        'inputs': [
            {
                'components': [
                    {'internalType': 'uint256', 'name': 'itemId', 'type': 'uint256'},
                    {'internalType': 'uint256', 'name': 'orderId', 'type': 'uint256'},
                    {'internalType': 'uint256', 'name': 'currencyId', 'type': 'uint256'},
                    {'internalType': 'uint256', 'name': 'count', 'type': 'uint256'},
                    {'internalType': 'address', 'name': 'account', 'type': 'address'},
                    {'internalType': 'uint256', 'name': 'price', 'type': 'uint256'},
                    {'internalType': 'uint256', 'name': 'timeout', 'type': 'uint256'},
                    {'internalType': 'uint256', 'name': 'salt', 'type': 'uint256'},
                ],
                'internalType': 'struct SnailTrailShop.ShopItem',
                'name': 'item',
                'type': 'tuple',
            },
            {'internalType': 'bytes', 'name': 'sig', 'type': 'bytes'},
        ],
        'name': 'buyItem',
        'outputs': [],
        'stateMutability': 'payable',
        'type': 'function',
    },
    {'inputs': [], 'name': 'enableShop', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
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
        'name': 'isShopEnabled',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'nftContract',
        'outputs': [{'internalType': 'contract ISnailTrailNFT', 'name': '', 'type': 'address'}],
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
    {'inputs': [], 'name': 'pauseShop', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
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
        'inputs': [],
        'name': 'tokenContract',
        'outputs': [{'internalType': 'contract IERC20', 'name': '', 'type': 'address'}],
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
    {'inputs': [], 'name': 'withdrawBalance', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
    {
        'inputs': [{'internalType': 'contract IERC20', 'name': 'token', 'type': 'address'}],
        'name': 'withdrawErc20',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {'inputs': [], 'name': 'withdrawSLIME', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
    {'stateMutability': 'payable', 'type': 'receive'},
]
