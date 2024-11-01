# generated automatically from https://www.snailtrail.art/main.44a30b30721e5995.js - DO NOT MODIFY

CONTRACT = '0xfDC483EE4ff24d3a8580504a5D04128451972e1e'

ABI = [
    {
        'inputs': [
            {'internalType': 'address', 'name': 'nftAddress', 'type': 'address'},
            {'internalType': 'address', 'name': 'tokenAddress', 'type': 'address'},
        ],
        'stateMutability': 'nonpayable',
        'type': 'constructor',
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
            {'indexed': False, 'internalType': 'uint256', 'name': 'tokenId', 'type': 'uint256'},
            {'indexed': False, 'internalType': 'string', 'name': 'newName', 'type': 'string'},
        ],
        'name': 'SnailNameChanged',
        'type': 'event',
    },
    {
        'anonymous': False,
        'inputs': [
            {'indexed': False, 'internalType': 'uint256', 'name': 'tokenId', 'type': 'uint256'},
            {'indexed': False, 'internalType': 'string', 'name': 'newName', 'type': 'string'},
        ],
        'name': 'SnailNamePaidChanged',
        'type': 'event',
    },
    {'stateMutability': 'payable', 'type': 'fallback'},
    {
        'inputs': [],
        'name': 'GENDER_DURATION',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'baseChangePrice',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'uint256', 'name': 'tokenId', 'type': 'uint256'},
            {'internalType': 'string', 'name': 'newName', 'type': 'string'},
        ],
        'name': 'buySnailNameChange',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'uint256', 'name': 'tokenId', 'type': 'uint256'},
            {'internalType': 'string', 'name': 'newName', 'type': 'string'},
        ],
        'name': 'forceNameChange',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': 'tokenId', 'type': 'uint256'}],
        'name': 'getCurrentNameChangePrice',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': 'tokenId', 'type': 'uint256'}],
        'name': 'getNameChangeCount',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': 'tokenId', 'type': 'uint256'}],
        'name': 'getSnailName',
        'outputs': [{'internalType': 'string', 'name': '', 'type': 'string'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': 'tokenId', 'type': 'uint256'}],
        'name': 'isAllFreeChangeUsed',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'isAutoAdjusted',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'isNameChangeEnabled',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'isNameChangePurchaseEnabled',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'string', 'name': 'name', 'type': 'string'}],
        'name': 'isNameTaken',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'maxNameChange',
        'outputs': [{'internalType': 'uint8', 'name': '', 'type': 'uint8'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'nameChangeIncreaseRate',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'nameChangePrice',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'nftContract',
        'outputs': [{'internalType': 'contract IERC721', 'name': '', 'type': 'address'}],
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
        'inputs': [{'internalType': 'bool', 'name': 'isEnabled', 'type': 'bool'}],
        'name': 'setIsUsingAutoAdjust',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint8', 'name': 'newAmount', 'type': 'uint8'}],
        'name': 'setMaxNameChange',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': 'newPrice', 'type': 'uint256'}],
        'name': 'setNameBaseChangePrice',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'bool', 'name': 'isEnabled', 'type': 'bool'}],
        'name': 'setNameChangeEnabled',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': 'newPrice', 'type': 'uint256'}],
        'name': 'setNameChangePrice',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': 'newPriceRate', 'type': 'uint256'}],
        'name': 'setNameChangePriceRate',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'bool', 'name': 'isEnabled', 'type': 'bool'}],
        'name': 'setNameChangePurchaseEnabled',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'uint256', 'name': 'tokenId', 'type': 'uint256'},
            {'internalType': 'string', 'name': 'newName', 'type': 'string'},
        ],
        'name': 'setSnailName',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'name': 'snailNames',
        'outputs': [{'internalType': 'string', 'name': '', 'type': 'string'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'bytes32', 'name': '', 'type': 'bytes32'}],
        'name': 'takenNames',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
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
    {'inputs': [], 'name': 'withdrawErc20', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
    {'stateMutability': 'payable', 'type': 'receive'},
]
