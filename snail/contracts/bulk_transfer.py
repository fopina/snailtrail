# generated automatically - DO NOT MODIFY

CONTRACT = '0xee5b5376d71d4af51bdc64ca353f51485fa8d6d5'

ABI = [
    {
        'inputs': [
            {'internalType': 'address', 'name': 'token', 'type': 'address'},
            {
                'components': [
                    {'internalType': 'address', 'name': 'to', 'type': 'address'},
                    {'internalType': 'uint256', 'name': 'amountOrTokenId', 'type': 'uint256'},
                ],
                'internalType': 'struct BulkTransfer.Call[]',
                'name': 'calls',
                'type': 'tuple[]',
            },
        ],
        'name': 'bulkTransfer20',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'address', 'name': 'token', 'type': 'address'},
            {
                'components': [
                    {'internalType': 'address', 'name': 'to', 'type': 'address'},
                    {'internalType': 'uint256', 'name': 'amountOrTokenId', 'type': 'uint256'},
                ],
                'internalType': 'struct BulkTransfer.Call[]',
                'name': 'calls',
                'type': 'tuple[]',
            },
        ],
        'name': 'bulkTransfer721',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'address', 'name': 'token', 'type': 'address'},
            {'internalType': 'address', 'name': 'to', 'type': 'address'},
            {'internalType': 'uint256[]', 'name': 'tokenIds', 'type': 'uint256[]'},
        ],
        'name': 'bulkTransfer721Lite',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
]
