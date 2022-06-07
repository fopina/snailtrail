PREFERENCES = [
    {
        "inputs": [
            {"internalType": "address", "name": "nftAddress", "type": "address"},
            {"internalType": "address", "name": "tokenAddress", "type": "address"},
        ],
        "stateMutability": "nonpayable",
        "type": "constructor",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "previousOwner",
                "type": "address",
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "newOwner",
                "type": "address",
            },
        ],
        "name": "OwnershipTransferred",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "tokenId",
                "type": "uint256",
            },
            {
                "indexed": False,
                "internalType": "string",
                "name": "newName",
                "type": "string",
            },
        ],
        "name": "SnailNameChanged",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "tokenId",
                "type": "uint256",
            },
            {
                "indexed": False,
                "internalType": "string",
                "name": "newName",
                "type": "string",
            },
        ],
        "name": "SnailNamePaidChanged",
        "type": "event",
    },
    {"stateMutability": "payable", "type": "fallback"},
    {
        "inputs": [],
        "name": "GENDER_DURATION",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "baseChangePrice",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "tokenId", "type": "uint256"},
            {"internalType": "string", "name": "newName", "type": "string"},
        ],
        "name": "buySnailNameChange",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "tokenId", "type": "uint256"},
            {"internalType": "string", "name": "newName", "type": "string"},
        ],
        "name": "forceNameChange",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "getCurrentNameChangePrice",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "getNameChangeCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "getSnailName",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "isAllFreeChangeUsed",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "isAutoAdjusted",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "isNameChangeEnabled",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "isNameChangePurchaseEnabled",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "string", "name": "name", "type": "string"}],
        "name": "isNameTaken",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "maxNameChange",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "nameChangeIncreaseRate",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "nameChangePrice",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "nftContract",
        "outputs": [
            {"internalType": "contract IERC721", "name": "", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "renounceOwnership",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bool", "name": "isEnabled", "type": "bool"}],
        "name": "setIsUsingAutoAdjust",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint8", "name": "newAmount", "type": "uint8"}],
        "name": "setMaxNameChange",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "newPrice", "type": "uint256"}],
        "name": "setNameBaseChangePrice",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bool", "name": "isEnabled", "type": "bool"}],
        "name": "setNameChangeEnabled",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "newPrice", "type": "uint256"}],
        "name": "setNameChangePrice",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "newPriceRate", "type": "uint256"}
        ],
        "name": "setNameChangePriceRate",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bool", "name": "isEnabled", "type": "bool"}],
        "name": "setNameChangePurchaseEnabled",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "tokenId", "type": "uint256"},
            {"internalType": "string", "name": "newName", "type": "string"},
        ],
        "name": "setSnailName",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "snailNames",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "name": "takenNames",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "tokenContract",
        "outputs": [{"internalType": "contract IERC20", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "newOwner", "type": "address"}],
        "name": "transferOwnership",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "withdrawBalance",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "withdrawErc20",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {"stateMutability": "payable", "type": "receive"},
]

RACE = [
    {
        "inputs": [
            {"internalType": "address", "name": "nftAddress", "type": "address"},
            {"internalType": "address", "name": "tokenAddress", "type": "address"},
        ],
        "stateMutability": "nonpayable",
        "type": "constructor",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "raceID",
                "type": "uint256",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "tokenID",
                "type": "uint256",
            },
            {
                "indexed": False,
                "internalType": "address",
                "name": "racerAddress",
                "type": "address",
            },
        ],
        "name": "JoinedCompetitiveRace",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "raceID",
                "type": "uint256",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "tokenID",
                "type": "uint256",
            },
            {
                "indexed": False,
                "internalType": "address",
                "name": "racerAddress",
                "type": "address",
            },
        ],
        "name": "JoinedDailyRace",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "previousOwner",
                "type": "address",
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "newOwner",
                "type": "address",
            },
        ],
        "name": "OwnershipTransferred",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "raceID",
                "type": "uint256",
            }
        ],
        "name": "RewardDistributed",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "address",
                "name": "beneficary",
                "type": "address",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256",
            },
        ],
        "name": "RewardsIssued",
        "type": "event",
    },
    {"stateMutability": "payable", "type": "fallback"},
    {
        "inputs": [],
        "name": "autoClaimAfterResultEnabled",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "claimRewards",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "claimableCompRewards",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "claimableDailyRewards",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "claimableRewards",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "compRewardTracker",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "compTreasuryContract",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "competitiveDistr",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "competitiveTotalDistr",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "competitveRaceMaxRacerTracker",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "address", "name": "", "type": "address"},
        ],
        "name": "competitveRaceUniqueEntryTracker",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "dailyRewardTracker",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "dailyTreasuryContract",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "uint256", "name": "raceID", "type": "uint256"},
                    {"internalType": "uint256", "name": "tokenID", "type": "uint256"},
                    {"internalType": "address", "name": "owner", "type": "address"},
                ],
                "internalType": "struct SnailTrailRace.RaceInfo",
                "name": "raceInfo",
                "type": "tuple",
            },
            {"internalType": "uint256", "name": "resultSize", "type": "uint256"},
            {
                "components": [
                    {"internalType": "uint256", "name": "raceID", "type": "uint256"},
                    {
                        "internalType": "address[]",
                        "name": "owners",
                        "type": "address[]",
                    },
                ],
                "internalType": "struct SnailTrailRace.RaceResult",
                "name": "raceResult0",
                "type": "tuple",
            },
            {"internalType": "uint256", "name": "timeout", "type": "uint256"},
            {"internalType": "uint256", "name": "salt", "type": "uint256"},
            {"internalType": "bytes", "name": "sig", "type": "bytes"},
        ],
        "name": "fallbackJoinDailyMission",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "fastResultEnabled",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "uint256", "name": "raceID", "type": "uint256"},
                    {
                        "internalType": "address[]",
                        "name": "owners",
                        "type": "address[]",
                    },
                ],
                "internalType": "struct SnailTrailRace.RaceResult",
                "name": "result",
                "type": "tuple",
            }
        ],
        "name": "forceRewardAllocation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "uint256", "name": "raceID", "type": "uint256"},
                    {
                        "internalType": "address[]",
                        "name": "owners",
                        "type": "address[]",
                    },
                ],
                "internalType": "struct SnailTrailRace.RaceResult[]",
                "name": "results",
                "type": "tuple[]",
            }
        ],
        "name": "forceRewardAllocations",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "owner", "type": "address"}],
        "name": "getCurrentNonce",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256[]", "name": "raceIDs", "type": "uint256[]"}
        ],
        "name": "getRacerCount",
        "outputs": [{"internalType": "uint256[]", "name": "", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "isCompetitiveRacesEnabled",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "isDailyMissionsEnabled",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "isRewardClaimEnabled",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "uint256", "name": "raceID", "type": "uint256"},
                    {"internalType": "uint256", "name": "tokenID", "type": "uint256"},
                    {"internalType": "address", "name": "owner", "type": "address"},
                    {"internalType": "uint256", "name": "fee", "type": "uint256"},
                    {
                        "internalType": "uint256",
                        "name": "resultSize",
                        "type": "uint256",
                    },
                ],
                "internalType": "struct SnailTrailRace.CompetitiveRaceInfo",
                "name": "raceInfo",
                "type": "tuple",
            },
            {
                "components": [
                    {"internalType": "uint256", "name": "raceID", "type": "uint256"},
                    {
                        "internalType": "address[]",
                        "name": "owners",
                        "type": "address[]",
                    },
                ],
                "internalType": "struct SnailTrailRace.RaceResult",
                "name": "raceResult0",
                "type": "tuple",
            },
            {"internalType": "uint256", "name": "timeout", "type": "uint256"},
            {"internalType": "uint256", "name": "salt", "type": "uint256"},
            {"internalType": "bytes", "name": "sig", "type": "bytes"},
        ],
        "name": "joinCompetitiveRace",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "uint256", "name": "raceID", "type": "uint256"},
                    {"internalType": "uint256", "name": "tokenID", "type": "uint256"},
                    {"internalType": "address", "name": "owner", "type": "address"},
                ],
                "internalType": "struct SnailTrailRace.RaceInfo",
                "name": "raceInfo",
                "type": "tuple",
            },
            {"internalType": "uint256", "name": "resultSize", "type": "uint256"},
            {
                "components": [
                    {
                        "components": [
                            {
                                "internalType": "uint256",
                                "name": "raceID",
                                "type": "uint256",
                            },
                            {
                                "internalType": "address[]",
                                "name": "owners",
                                "type": "address[]",
                            },
                        ],
                        "internalType": "struct SnailTrailRace.RaceResult",
                        "name": "result1",
                        "type": "tuple",
                    },
                    {
                        "components": [
                            {
                                "internalType": "uint256",
                                "name": "raceID",
                                "type": "uint256",
                            },
                            {
                                "internalType": "address[]",
                                "name": "owners",
                                "type": "address[]",
                            },
                        ],
                        "internalType": "struct SnailTrailRace.RaceResult",
                        "name": "result2",
                        "type": "tuple",
                    },
                ],
                "internalType": "struct SnailTrailRace.ResultWrapper",
                "name": "results",
                "type": "tuple",
            },
            {"internalType": "uint256", "name": "timeout", "type": "uint256"},
            {"internalType": "uint256", "name": "salt", "type": "uint256"},
            {"internalType": "bytes", "name": "sig", "type": "bytes"},
        ],
        "name": "joinDailyMission",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "nonceCounter",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "uint256", "name": "raceID", "type": "uint256"},
                    {
                        "internalType": "address[]",
                        "name": "owners",
                        "type": "address[]",
                    },
                ],
                "internalType": "struct SnailTrailRace.RaceResult[]",
                "name": "results",
                "type": "tuple[]",
            },
            {"internalType": "uint256", "name": "nonce", "type": "uint256"},
            {"internalType": "bytes", "name": "sig", "type": "bytes"},
        ],
        "name": "postResults",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "resultSize", "type": "uint256"},
            {
                "components": [
                    {
                        "components": [
                            {
                                "internalType": "uint256",
                                "name": "raceID",
                                "type": "uint256",
                            },
                            {
                                "internalType": "address[]",
                                "name": "owners",
                                "type": "address[]",
                            },
                        ],
                        "internalType": "struct SnailTrailRace.RaceResult",
                        "name": "result1",
                        "type": "tuple",
                    },
                    {
                        "components": [
                            {
                                "internalType": "uint256",
                                "name": "raceID",
                                "type": "uint256",
                            },
                            {
                                "internalType": "address[]",
                                "name": "owners",
                                "type": "address[]",
                            },
                        ],
                        "internalType": "struct SnailTrailRace.RaceResult",
                        "name": "result2",
                        "type": "tuple",
                    },
                ],
                "internalType": "struct SnailTrailRace.ResultWrapper",
                "name": "results",
                "type": "tuple",
            },
            {"internalType": "uint256", "name": "nonce", "type": "uint256"},
            {"internalType": "bytes", "name": "sig", "type": "bytes"},
        ],
        "name": "postResultsFixed",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "preCalculatedDailyRewards",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "raceFeeTracker",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "uint256", "name": "", "type": "uint256"},
        ],
        "name": "raceIDToAddress",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "raceSubmissionTracker",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "raceTypeTracker",
        "outputs": [
            {"internalType": "enum SnailRaceType", "name": "", "type": "uint8"}
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "renounceOwnership",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "rewardDistributionTracker",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bool", "name": "isEnabled", "type": "bool"}],
        "name": "setAutoClaimAfterResultEnabled",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "newAddress", "type": "address"}
        ],
        "name": "setCompTreasuryContract",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256[]", "name": "newDist", "type": "uint256[]"}
        ],
        "name": "setCompetitiveDist",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bool", "name": "isEnabled", "type": "bool"}],
        "name": "setCompetitiveRacesEnabled",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256[]", "name": "newDist", "type": "uint256[]"}
        ],
        "name": "setDailyMissionDist",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "rewardAmount", "type": "uint256"}
        ],
        "name": "setDailyMissionReward",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bool", "name": "isEnabled", "type": "bool"}],
        "name": "setDailyMissionsEnabled",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "newAddress", "type": "address"}
        ],
        "name": "setDailyTreasuryContract",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bool", "name": "isEnabled", "type": "bool"}],
        "name": "setFastResultEnabled",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bool", "name": "isEnabled", "type": "bool"}],
        "name": "setRewardClaimEnabled",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "newAddress", "type": "address"}
        ],
        "name": "setSigner",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "signerPublicAddress",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "newOwner", "type": "address"}],
        "name": "transferOwnership",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "withdrawBalance",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "withdrawErc20",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {"stateMutability": "payable", "type": "receive"},
]
