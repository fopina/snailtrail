# generated automatically from https://www.snailtrail.art/main.d3905bf907602c39.js - DO NOT MODIFY

CONTRACT = '0xa65592fC7afa222Ac30a80F273280e6477a274e3'

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
            {'indexed': False, 'internalType': 'uint256', 'name': 'raceID', 'type': 'uint256'},
            {'indexed': False, 'internalType': 'uint256', 'name': 'tokenID', 'type': 'uint256'},
            {'indexed': False, 'internalType': 'address', 'name': 'racerAddress', 'type': 'address'},
        ],
        'name': 'JoinedMegaRace',
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
        'inputs': [{'indexed': False, 'internalType': 'uint256', 'name': 'raceID', 'type': 'uint256'}],
        'name': 'RewardDistributed',
        'type': 'event',
    },
    {
        'anonymous': False,
        'inputs': [
            {'indexed': False, 'internalType': 'address', 'name': 'beneficary', 'type': 'address'},
            {'indexed': False, 'internalType': 'uint256', 'name': 'amount', 'type': 'uint256'},
        ],
        'name': 'RewardsIssued',
        'type': 'event',
    },
    {'stateMutability': 'payable', 'type': 'fallback'},
    {'inputs': [], 'name': 'claimRewards', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
    {
        'inputs': [],
        'name': 'claimableRewards',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'directResultEnabled',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'address', 'name': 'nftAddress', 'type': 'address'},
            {'internalType': 'address', 'name': 'tokenAddress', 'type': 'address'},
            {'internalType': 'address', 'name': 'wavaxAddress', 'type': 'address'},
        ],
        'name': 'initialize',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'isRewardClaimEnabled',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [
            {
                'components': [
                    {'internalType': 'uint256', 'name': 'raceID', 'type': 'uint256'},
                    {'internalType': 'uint256', 'name': 'tokenID', 'type': 'uint256'},
                    {'internalType': 'address', 'name': 'owner', 'type': 'address'},
                    {'internalType': 'uint256', 'name': 'fee', 'type': 'uint256'},
                    {'internalType': 'uint256', 'name': 'resultSize', 'type': 'uint256'},
                    {'internalType': 'uint256', 'name': 'timeout', 'type': 'uint256'},
                ],
                'internalType': 'struct SnailTrailMegaRace.CompetitiveRaceInfo',
                'name': 'raceInfo',
                'type': 'tuple',
            },
            {
                'components': [
                    {'internalType': 'uint256', 'name': 'raceID', 'type': 'uint256'},
                    {'internalType': 'address[]', 'name': 'winners', 'type': 'address[]'},
                    {'internalType': 'uint256[]', 'name': 'rewards', 'type': 'uint256[]'},
                ],
                'internalType': 'struct SnailTrailMegaRace.RaceResult',
                'name': 'raceResult',
                'type': 'tuple',
            },
            {'internalType': 'uint256', 'name': 'salt', 'type': 'uint256'},
            {'internalType': 'bytes', 'name': 'sig', 'type': 'bytes'},
        ],
        'name': 'joinMegaRace',
        'outputs': [],
        'stateMutability': 'payable',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'megaRacesEnabled',
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
    {
        'inputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'name': 'racerCountbyRaceId',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {'inputs': [], 'name': 'renounceOwnership', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'},
    {
        'inputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'name': 'rewardDistributionTracker',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'address', 'name': '', 'type': 'address'}],
        'name': 'rewardTracker',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'bool', 'name': 'isEnabled', 'type': 'bool'}],
        'name': 'setMegaRacesEnabled',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'address', 'name': 'newAddress', 'type': 'address'}],
        'name': 'setSigner',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'address', 'name': 'newAddress', 'type': 'address'}],
        'name': 'setWavaxTreasuryContract',
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
        'inputs': [],
        'name': 'wavaxTreasuryContract',
        'outputs': [{'internalType': 'address', 'name': '', 'type': 'address'}],
        'stateMutability': 'view',
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
    {'stateMutability': 'payable', 'type': 'receive'},
]