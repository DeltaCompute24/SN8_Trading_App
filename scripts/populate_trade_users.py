from scripts.populate_transactions import get_user
from src.database_tasks import TaskSessionLocal_
from src.models.users import Users

ambassadors = {
    "5CRwSWfJWnMat1wtUvLTLUJ3ekTTgn1XDC8jVko2H9CmnYC1": 4040,
    "5ERQp6a5Cd5MsTNnmXQsfrrRoiFvXy6ojE734Z4NxTmaEiiZ": 4041,
    "5DUdBHPKqwB3Pv85suEZxSyf8EVfcV9V4iPyZaEAMfvzBkp6": 4042,
    "5FKqNPgDrZCwo4GgMAjTo77L4KRTNcQgpzMWASvDGPRJGZRP": 4043,
    "5Ew171L2s9RX2wZXbPwS1kcmhyAjzEXSG5W9551bcRqsL3Pg": 4070,
    "5ERNiynJejVeK6BtHXyyBJNB6RXNzwERhgHjcK7jbNT4n9xQ": 4071,
    "5DthKaDbqEauMm25rKmKQCjJYvbshR84NzhAVT4zLq4Dz4qK": 4072,
    "5HK2szxDvXpGzCdSvsRH4hctbVQcDneizgcqgsaWxLAA8e5f": 4073,
    "5Fc39mqXCJrkwVLTZCduUgkmkUv7Rsz2kgtkHQVMQo8ZTn5U": 4063,
    "5GCDZ6Vum2vj1YgKtw7Kv2fVXTPmV1pxoHh1YrsxqBvf9SRa": 4064,
    "5GTL7WXa4JM2yEUjFoCy2PZVLioNs1HzAGLKhuCDzzoeQCTR": 4065,
    "5DoCFr2EoW1CGuYCEXhsuQdWRsgiUMuxGwNt4Xqb5TCptcBW": 4067,
    "5EUTaAo7vCGxvLDWRXRrEuqctPjt9fKZmgkaeFZocWECUe9X": 4068,
}


def populate_trade_users():
    with TaskSessionLocal_() as db:
        for hot_key, trader_id in ambassadors.items():
            try:
                user = get_user(db, hot_key)
                if not user:
                    new_user = Users(
                        trader_id=trader_id,
                        hot_key=hot_key,
                    )
                    db.add(new_user)
                    db.commit()
                    db.refresh(new_user)
            except Exception as ex:
                print(f"Error while creating trader_id and hot_key: {hot_key}")


populate_trade_users()
