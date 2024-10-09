from scripts.populate_trade_users import ambassadors
from src.database_tasks import TaskSessionLocal_
from src.models.challenge import Challenge

challenges_dict = {
    '5CRwSWfJWnMat1wtUvLTLUJ3ekTTgn1XDC8jVko2H9CmnYC1': 4040,
    '5DUdBHPKqwB3Pv85suEZxSyf8EVfcV9V4iPyZaEAMfvzBkp6': 4042,
    '5DoCFr2EoW1CGuYCEXhsuQdWRsgiUMuxGwNt4Xqb5TCptcBW': 4067,
    '5DthKaDbqEauMm25rKmKQCjJYvbshR84NzhAVT4zLq4Dz4qK': 4072,
    '5EHtvpzc9zMeYeB4yiAgyBLMaVbeF5SS72B2vKNwWMcsESXM': 4041,
    '5ERNiynJejVeK6BtHXyyBJNB6RXNzwERhgHjcK7jbNT4n9xQ': 4071,
    '5ERQp6a5Cd5MsTNnmXQsfrrRoiFvXy6ojE734Z4NxTmaEiiZ': 4041,
    '5EUTaAo7vCGxvLDWRXRrEuqctPjt9fKZmgkaeFZocWECUe9X': 4068,
    '5Ew171L2s9RX2wZXbPwS1kcmhyAjzEXSG5W9551bcRqsL3Pg': 4070,
    '5FKqNPgDrZCwo4GgMAjTo77L4KRTNcQgpzMWASvDGPRJGZRP': 4043,
    '5Fc39mqXCJrkwVLTZCduUgkmkUv7Rsz2kgtkHQVMQo8ZTn5U': 4063,
    '5GCDZ6Vum2vj1YgKtw7Kv2fVXTPmV1pxoHh1YrsxqBvf9SRa': 4044,
    '5GTL7WXa4JM2yEUjFoCy2PZVLioNs1HzAGLKhuCDzzoeQCTR': 4065,
    '5HK2szxDvXpGzCdSvsRH4hctbVQcDneizgcqgsaWxLAA8e5f': 4073,
    'aaa': 22
}


def trades_mapper():
    ambassadors2 = {}
    with TaskSessionLocal_() as db:
        challenges = db.query(Challenge).all()
        for challenge in challenges:
            ambassadors2[challenge.hot_key] = challenge.trader_id

    print(ambassadors2)
    diff = {key: (ambassadors[key], ambassadors2[key]) for key in ambassadors if
            key in ambassadors2 and ambassadors[key] != ambassadors2[key]}

    print(diff)


trades_mapper()
