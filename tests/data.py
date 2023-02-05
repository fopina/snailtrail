from hexbytes import HexBytes
from web3.datastructures import AttributeDict

# example of a transaction hash returned by web.eth `send_raw_transaction`
TX_HASH = b'\xd0\x16\xbf\xcba\xc1\x1d\xfb\xe5+C\xaa\xd7\xf7l\x9am\x00OQ\x92\x0eL\xfb\x1d*\x81\xaee\x8b\xf4\xc7'

# example of a "transaction receipt" returned by `wait_for_transaction_receipt`

# receipt for TX_HASH above
TX_RECEIPT_1 = AttributeDict(
    {
        'blockHash': HexBytes('0x3604afa3e4db41132181795a5e7c41900ec4c7ef737bce7405371bf62b157867'),
        'blockNumber': 25864677,
        'contractAddress': None,
        'cumulativeGasUsed': 459624,
        'effectiveGasPrice': 25000000000,
        'from': '0xd991975e1C72E43C5702ced3230dA484442F195a',
        'gasUsed': 88511,
        'logs': [
            AttributeDict(
                {
                    'address': '0x5a15Bdcf9a3A8e799fa4381E666466a516F2d9C8',
                    'topics': [
                        HexBytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),
                        HexBytes('0x000000000000000000000000450324d8c9a7abf3b1626d590cf4beb48366d3b8'),
                        HexBytes('0x00000000000000000000000058b699642f2a4b91dd10800ef852427b719db1f0'),
                    ],
                    'data': '0x000000000000000000000000000000000000000000045bac3bf97a30d24b0000',
                    'blockNumber': 25864677,
                    'transactionHash': HexBytes('0xd016bfcb61c11dfbe52b43aad7f76c9a6d004f51920e4cfb1d2a81ae658bf4c7'),
                    'transactionIndex': 1,
                    'blockHash': HexBytes('0x3604afa3e4db41132181795a5e7c41900ec4c7ef737bce7405371bf62b157867'),
                    'logIndex': 9,
                    'removed': False,
                }
            ),
            AttributeDict(
                {
                    'address': '0x5a15Bdcf9a3A8e799fa4381E666466a516F2d9C8',
                    'topics': [
                        HexBytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                        HexBytes('0x000000000000000000000000450324d8c9a7abf3b1626d590cf4beb48366d3b8'),
                        HexBytes('0x000000000000000000000000d991975e1c72e43c5702ced3230da484442f195a'),
                    ],
                    'data': '0x00000000000000000000000000000000000000000000001d6fa387100d1c0000',
                    'blockNumber': 25864677,
                    'transactionHash': HexBytes('0xd016bfcb61c11dfbe52b43aad7f76c9a6d004f51920e4cfb1d2a81ae658bf4c7'),
                    'transactionIndex': 1,
                    'blockHash': HexBytes('0x3604afa3e4db41132181795a5e7c41900ec4c7ef737bce7405371bf62b157867'),
                    'logIndex': 10,
                    'removed': False,
                }
            ),
            AttributeDict(
                {
                    'address': '0x58B699642f2a4b91Dd10800Ef852427B719dB1f0',
                    'topics': [HexBytes('0x5ff025b21b33bb30a2582ff811cb9c5cf9804a5aaa375929b8b910383ec31d22')],
                    'data': '0x000000000000000000000000d991975e1c72e43c5702ced3230da484442f195a00000000000000000000000000000000000000000000001d6fa387100d1c0000',
                    'blockNumber': 25864677,
                    'transactionHash': HexBytes('0xd016bfcb61c11dfbe52b43aad7f76c9a6d004f51920e4cfb1d2a81ae658bf4c7'),
                    'transactionIndex': 1,
                    'blockHash': HexBytes('0x3604afa3e4db41132181795a5e7c41900ec4c7ef737bce7405371bf62b157867'),
                    'logIndex': 11,
                    'removed': False,
                }
            ),
        ],
        'logsBloom': HexBytes(
            '0x00000000000000000000000000000000000010000004000000000000000000000000000000000200000008000002000000000000000000000000000000200000000000000000000000008008000000000000000000000000000000000000000000000000000000000000080000040000000000000000000001000010000000000004000000000000000000000000000000000000000000000000000000000000020008000000000000000000000000000000000000000000000000000000000000010006000000000000000000000001000000000004000000000800020000000010000000000000000000000000000000000010000000000000000000000000'
        ),
        'status': 1,
        'to': '0x58B699642f2a4b91Dd10800Ef852427B719dB1f0',
        'transactionHash': HexBytes('0xd016bfcb61c11dfbe52b43aad7f76c9a6d004f51920e4cfb1d2a81ae658bf4c7'),
        'transactionIndex': 1,
        'type': '0x2',
    }
)
TX_RECEIPT_2 = AttributeDict(
    {
        'blockHash': HexBytes('0x3604afa3e4db41132181795a5e7c41900ec4c7ef737bce7405371bf62b157867'),
        'blockNumber': 25864677,
        'contractAddress': None,
        'cumulativeGasUsed': 548135,
        'effectiveGasPrice': 25000000000,
        'from': '0xccBc66c9Dea9dFeAE0e57370Ee5974bed117bB35',
        'gasUsed': 88511,
        'logs': [
            AttributeDict(
                {
                    'address': '0x5a15Bdcf9a3A8e799fa4381E666466a516F2d9C8',
                    'topics': [
                        HexBytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),
                        HexBytes('0x000000000000000000000000450324d8c9a7abf3b1626d590cf4beb48366d3b8'),
                        HexBytes('0x00000000000000000000000058b699642f2a4b91dd10800ef852427b719db1f0'),
                    ],
                    'data': '0x000000000000000000000000000000000000000000045b8ea2b3cf05cf030000',
                    'blockNumber': 25864677,
                    'transactionHash': HexBytes('0x5200f9d11a93c68788623e1536f93fd2192b9e3b97b5cfb7223383c84ac7430a'),
                    'transactionIndex': 2,
                    'blockHash': HexBytes('0x3604afa3e4db41132181795a5e7c41900ec4c7ef737bce7405371bf62b157867'),
                    'logIndex': 12,
                    'removed': False,
                }
            ),
            AttributeDict(
                {
                    'address': '0x5a15Bdcf9a3A8e799fa4381E666466a516F2d9C8',
                    'topics': [
                        HexBytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                        HexBytes('0x000000000000000000000000450324d8c9a7abf3b1626d590cf4beb48366d3b8'),
                        HexBytes('0x000000000000000000000000ccbc66c9dea9dfeae0e57370ee5974bed117bb35'),
                    ],
                    'data': '0x00000000000000000000000000000000000000000000001d9945ab2b03480000',
                    'blockNumber': 25864677,
                    'transactionHash': HexBytes('0x5200f9d11a93c68788623e1536f93fd2192b9e3b97b5cfb7223383c84ac7430a'),
                    'transactionIndex': 2,
                    'blockHash': HexBytes('0x3604afa3e4db41132181795a5e7c41900ec4c7ef737bce7405371bf62b157867'),
                    'logIndex': 13,
                    'removed': False,
                }
            ),
            AttributeDict(
                {
                    'address': '0x58B699642f2a4b91Dd10800Ef852427B719dB1f0',
                    'topics': [HexBytes('0x5ff025b21b33bb30a2582ff811cb9c5cf9804a5aaa375929b8b910383ec31d22')],
                    'data': '0x000000000000000000000000ccbc66c9dea9dfeae0e57370ee5974bed117bb3500000000000000000000000000000000000000000000001d9945ab2b03480000',
                    'blockNumber': 25864677,
                    'transactionHash': HexBytes('0x5200f9d11a93c68788623e1536f93fd2192b9e3b97b5cfb7223383c84ac7430a'),
                    'transactionIndex': 2,
                    'blockHash': HexBytes('0x3604afa3e4db41132181795a5e7c41900ec4c7ef737bce7405371bf62b157867'),
                    'logIndex': 14,
                    'removed': False,
                }
            ),
        ],
        'logsBloom': HexBytes(
            '0x00000000000000000000000000000000000010000004000000000000000000000000000000000200000008000002000000000000800000000000000000200000000000000000000000008008000000000000000000000000000000000000000000000000000000004000080000040000000000000000000001000010000000000004000000020000000000000000000000000000000000000000000000000000020008000000000000000000000000000000000000000000000000000000000000010002000000000000000000000001000000000000000000000000020000000010000000000000000000000000000000000010000000000000000000000000'
        ),
        'status': 1,
        'to': '0x58B699642f2a4b91Dd10800Ef852427B719dB1f0',
        'transactionHash': HexBytes('0x5200f9d11a93c68788623e1536f93fd2192b9e3b97b5cfb7223383c84ac7430a'),
        'transactionIndex': 2,
        'type': '0x2',
    }
)

GQL_MISSION_SNAILS = {
    'snails': [
        {
            'id': 8922,
            'adaptations': ['Wind', 'Slide'],
            'name': 'Snail #8922',
            'queueable_at': '2021-08-09 23:32:27.108936',
            'stats': {
                'mission_tickets': -104,
                'experience': {'level': 8, 'xp': 1770, 'remaining': 230},
                '__typename': 'DashboardStats',
            },
            '__typename': 'Snail',
        },
        {
            'id': 9104,
            'adaptations': ['Mountain', 'Cold'],
            'name': 'Snail #9104',
            'queueable_at': '2021-08-09 23:45:10.742612',
            'stats': {
                'mission_tickets': -100,
                'experience': {'level': 5, 'xp': 1220, 'remaining': 30},
                '__typename': 'DashboardStats',
            },
            '__typename': 'Snail',
        },
        {
            'id': 8267,
            'adaptations': ['Cold', 'Beach'],
            'name': 'Powerpuff',
            'queueable_at': '2021-08-10 00:03:36.358478',
            'stats': {
                'mission_tickets': -100,
                'experience': {'level': 11, 'xp': 2950, 'remaining': 100},
                '__typename': 'DashboardStats',
            },
            '__typename': 'Snail',
        },
        {
            'id': 8416,
            'adaptations': ['Cold', 'Roll'],
            'name': 'Snail #8416',
            'queueable_at': '2021-08-10 00:16:06.700280',
            'stats': {
                'mission_tickets': -105,
                'experience': {'level': 10, 'xp': 2290, 'remaining': 310},
                '__typename': 'DashboardStats',
            },
            '__typename': 'Snail',
        },
        {
            'id': 8667,
            'adaptations': ['Cold', 'Dodge'],
            'name': 'Snail #8667',
            'queueable_at': '2021-08-10 00:47:51.918061',
            'stats': {
                'mission_tickets': -98,
                'experience': {'level': 9, 'xp': 2100, 'remaining': 150},
                '__typename': 'DashboardStats',
            },
            '__typename': 'Snail',
        },
        {
            'id': 8851,
            'adaptations': ['Jump', 'Glacier'],
            'name': 'SK006',
            'queueable_at': '2021-08-10 01:13:04.036512',
            'stats': {
                'mission_tickets': -85,
                'experience': {'level': 8, 'xp': 1995, 'remaining': 5},
                '__typename': 'DashboardStats',
            },
            '__typename': 'Snail',
        },
        {
            'id': 8813,
            'adaptations': ['Mountain', 'Slide'],
            'name': 'Snail #8813',
            'queueable_at': '2021-08-10 01:22:44.489910',
            'stats': {
                'mission_tickets': -100,
                'experience': {'level': 8, 'xp': 1895, 'remaining': 105},
                '__typename': 'DashboardStats',
            },
            '__typename': 'Snail',
        },
        {
            'id': 8860,
            'adaptations': ['Desert', 'Wind'],
            'name': 'Snail #8860',
            'queueable_at': '2021-08-10 01:39:50.960050',
            'stats': {
                'mission_tickets': -86,
                'experience': {'level': 8, 'xp': 1945, 'remaining': 55},
                '__typename': 'DashboardStats',
            },
            '__typename': 'Snail',
        },
        {
            'id': 8663,
            'adaptations': ['Roll', 'Snow'],
            'name': 'SK004',
            'queueable_at': '2021-08-10 02:07:32.175944',
            'stats': {
                'mission_tickets': -102,
                'experience': {'level': 10, 'xp': 2410, 'remaining': 190},
                '__typename': 'DashboardStats',
            },
            '__typename': 'Snail',
        },
        {
            'id': 8392,
            'adaptations': ['Jump', 'Space'],
            'name': 'Snail #8392',
            'queueable_at': '2021-08-10 03:23:56.308578',
            'stats': {
                'mission_tickets': -105,
                'experience': {'level': 10, 'xp': 2375, 'remaining': 225},
                '__typename': 'DashboardStats',
            },
            '__typename': 'Snail',
        },
    ],
    'count': 10,
    '__typename': 'Snails',
}

GQL_MISSION_RACES = {
    'all': [
        {
            'id': 169311,
            'conditions': ['Mountain', 'Cold', 'Slide'],
            'distance': 'Treasury Run',
            # 10 snails
            'athletes': [1161, 1946, 2218, 2266, 7655, 8003, 8803, 9189, 9408, 9525],
            'track': 'Hockenheimring',
            'participation': False,
            '__typename': 'Race',
        },
        {
            'id': 169396,
            'conditions': ['Forest', 'Wet', 'Dodge'],
            'distance': 'Treasury Run',
            # 9 snails
            'athletes': [1288, 2036, 2784, 4747, 7082, 7602, 8069, 9273, 9326],
            'track': 'Pulau Siput',
            'participation': False,
            '__typename': 'Race',
        },
        {
            'id': 169399,
            'conditions': ['Space', 'Storm', 'Jump'],
            'distance': 'Treasury Run',
            # 9 snails
            'athletes': [2126, 3925, 4765, 7104, 8168, 8458, 8957, 9911, 9989],
            'track': 'Bebbux',
            'participation': False,
            '__typename': 'Race',
        },
        {
            'id': 169400,
            'conditions': ['Space', 'Storm', 'Roll'],
            'distance': 'Treasury Run',
            # 9 snails
            'athletes': [2269, 2993, 4985, 6633, 6869, 7972, 8188, 9314, 9719],
            'track': 'Circuit de Spa',
            'participation': False,
            '__typename': 'Race',
        },
        {
            'id': 169401,
            'conditions': ['Beach', 'Cold', 'Jump'],
            'distance': 'Treasury Run',
            # 9 snails
            'athletes': [813, 1551, 2422, 5238, 5980, 8273, 8317, 9172, 9912],
            'track': 'Hockenheimring',
            'participation': False,
            '__typename': 'Race',
        },
        {
            'id': 169402,
            'conditions': ['Beach', 'Hot', 'Roll'],
            'distance': 'Treasury Run',
            # 9 snails
            'athletes': [760, 1573, 4624, 5355, 6216, 6406, 8382, 8441, 8527],
            'track': 'Shanghai',
            'participation': False,
            '__typename': 'Race',
        },
        {
            'id': 169403,
            'conditions': ['Forest', 'Snow', 'Dodge'],
            'distance': 'Treasury Run',
            # 9 snails
            'athletes': [2240, 2421, 2570, 3343, 5953, 5961, 7058, 7158, 8658],
            'track': 'Hockenheimring',
            'participation': False,
            '__typename': 'Race',
        },
        {
            'id': 169404,
            'conditions': ['Glacier', 'Wind', 'Roll'],
            'distance': 'Treasury Run',
            # 8 snails
            'athletes': [1123, 1629, 2206, 4071, 8766, 8922, 9317, 9940],
            'track': 'Circuit de Monaco',
            'participation': True,
            '__typename': 'Race',
        },
        {
            'id': 169405,
            'conditions': ['Forest', 'Wind', 'Dodge'],
            'distance': 'Treasury Run',
            # 5 snails
            'athletes': [6150, 6962, 8419, 8531, 9783],
            'track': 'Circuit de Monaco',
            'participation': False,
            '__typename': 'Race',
        },
        {
            'id': 169406,
            'conditions': ['Desert', 'Hot', 'Jump'],
            'distance': 'Treasury Run',
            # 4 snails
            'athletes': [5439, 6449, 8915, 9342],
            'track': 'Silverstone Circuit',
            'participation': False,
            '__typename': 'Race',
        },
    ],
    '__typename': 'Races',
}

GQL_FINISHED_RACES = {
    'own': [
        {
            'id': 169311,
            'conditions': ['Mountain', 'Cold', 'Slide'],
            'distance': 50,
            'results': [
                {'token_id': 1161},
                {'token_id': 1946},
                {'token_id': 9104},
                {'token_id': 2266},
                {'token_id': 7655},
                {'token_id': 8003},
                {'token_id': 8803},
                {'token_id': 8267},
                {'token_id': 9408},
            ],
            'rewards': {
                'final_distribution': [
                    6,
                    5,
                    4,
                    2,
                    1,
                    0,
                    0,
                    0,
                    0,
                ],
            },
            'track': 'Hockenheimring',
            'participation': False,
            '__typename': 'Race',
        },
    ],
    '__typename': 'Races',
}
