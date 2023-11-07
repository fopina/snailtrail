# generated automatically from https://www.snailtrail.art/main.44a30b30721e5995.js - DO NOT MODIFY

CONTRACT = '0xeb77bd67Bd607e5b7d9b78db82fad0DE395B5DeF'

ABI = [
    {
        'inputs': [{'internalType': 'address', 'name': 'nftAddress', 'type': 'address'}],
        'stateMutability': 'nonpayable',
        'type': 'constructor',
    },
    {
        'anonymous': False,
        'inputs': [
            {
                'components': [
                    {'internalType': 'uint256', 'name': 'itemId', 'type': 'uint256'},
                    {'internalType': 'uint256', 'name': 'tokenId', 'type': 'uint256'},
                    {'internalType': 'address payable', 'name': 'seller', 'type': 'address'},
                    {'internalType': 'uint256', 'name': 'price', 'type': 'uint256'},
                    {'internalType': 'bool', 'name': 'isListed', 'type': 'bool'},
                ],
                'indexed': False,
                'internalType': 'struct SnailTrailMarketplace.MarketItem',
                'name': 'newItem',
                'type': 'tuple',
            }
        ],
        'name': 'ListItem',
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
            {
                'components': [
                    {
                        'components': [
                            {'internalType': 'uint256', 'name': 'itemId', 'type': 'uint256'},
                            {'internalType': 'uint256', 'name': 'tokenId', 'type': 'uint256'},
                            {'internalType': 'address payable', 'name': 'seller', 'type': 'address'},
                            {'internalType': 'uint256', 'name': 'price', 'type': 'uint256'},
                            {'internalType': 'bool', 'name': 'isListed', 'type': 'bool'},
                        ],
                        'internalType': 'struct SnailTrailMarketplace.MarketItem',
                        'name': 'item',
                        'type': 'tuple',
                    },
                    {'internalType': 'address', 'name': 'buyer', 'type': 'address'},
                ],
                'indexed': False,
                'internalType': 'struct SnailTrailMarketplace.Purchase',
                'name': 'item',
                'type': 'tuple',
            }
        ],
        'name': 'PurchaseItem',
        'type': 'event',
    },
    {
        'anonymous': False,
        'inputs': [
            {
                'components': [
                    {'internalType': 'uint256', 'name': 'itemId', 'type': 'uint256'},
                    {'internalType': 'uint256', 'name': 'tokenId', 'type': 'uint256'},
                    {'internalType': 'address payable', 'name': 'seller', 'type': 'address'},
                    {'internalType': 'uint256', 'name': 'price', 'type': 'uint256'},
                    {'internalType': 'bool', 'name': 'isListed', 'type': 'bool'},
                ],
                'indexed': False,
                'internalType': 'struct SnailTrailMarketplace.MarketItem',
                'name': 'marketItem',
                'type': 'tuple',
            }
        ],
        'name': 'UpdateMarketItem',
        'type': 'event',
    },
    {
        'anonymous': False,
        'inputs': [{'indexed': False, 'internalType': 'uint256', 'name': 'tokenId', 'type': 'uint256'}],
        'name': 'Withdraw',
        'type': 'event',
    },
    {
        'inputs': [{'internalType': 'uint256[]', 'name': 'listingIDs', 'type': 'uint256[]'}],
        'name': 'emergencyDelist',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {'inputs': [], 'name': 'enableMarketplace', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
    {
        'inputs': [{'internalType': 'uint256', 'name': 'itemId', 'type': 'uint256'}],
        'name': 'fullfillSale',
        'outputs': [],
        'stateMutability': 'payable',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'getCurrentListCount',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'isBazaarOpen',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'uint256', 'name': 'tokenId', 'type': 'uint256'},
            {'internalType': 'uint256', 'name': 'price', 'type': 'uint256'},
        ],
        'name': 'listMarketItem',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'marketFee',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'name': 'marketItems',
        'outputs': [
            {'internalType': 'uint256', 'name': 'itemId', 'type': 'uint256'},
            {'internalType': 'uint256', 'name': 'tokenId', 'type': 'uint256'},
            {'internalType': 'address payable', 'name': 'seller', 'type': 'address'},
            {'internalType': 'uint256', 'name': 'price', 'type': 'uint256'},
            {'internalType': 'bool', 'name': 'isListed', 'type': 'bool'},
        ],
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
    {'inputs': [], 'name': 'pauseMarketplace', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
    {'inputs': [], 'name': 'renounceOwnership', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
    {
        'inputs': [{'internalType': 'address', 'name': 'newOwner', 'type': 'address'}],
        'name': 'transferOwnership',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': 'newMarketFee', 'type': 'uint256'}],
        'name': 'updateFees',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'uint256', 'name': 'itemId', 'type': 'uint256'},
            {'internalType': 'uint256', 'name': 'price', 'type': 'uint256'},
        ],
        'name': 'updatePrice',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {'inputs': [], 'name': 'withdrawBalance', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
    {
        'inputs': [{'internalType': 'uint256', 'name': 'itemId', 'type': 'uint256'}],
        'name': 'withdrawMarketItem',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
]
