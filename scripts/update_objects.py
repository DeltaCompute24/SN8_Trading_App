from sqlalchemy import select

from src.database_tasks import TaskSessionLocal_
from src.models.transaction import Transaction
from src.services.api_service import call_checkpoint_api, call_main_net
from src.services.user_service import get_challenge_for_hotkey

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


def process_data(data, mapper, uuid_list, source):
    for hot_key, content in data.items():
        challenge = get_challenge_for_hotkey(hot_key)
        if not challenge:
            continue

        positions = content["positions"]
        for position in positions:
            mapper[position["position_uuid"]] = source
            uuid_list.append(position["position_uuid"])

    return mapper, uuid_list


def update_transactions():
    with TaskSessionLocal_() as db:
        test_net_data = call_checkpoint_api()
        main_net_data = call_main_net()
        data = test_net_data | main_net_data

        result = db.execute(
            select(Transaction).where(Transaction.status != "CLOSED")
        )
        transactions = result.scalars().all()

        for obj in transactions:
            content = data.get(obj.hot_key)
            positions = content["positions"]
            for position in positions:
                if position["position_uuid"] != obj.uuid:
                    continue

                obj.order_level = len(position["orders"])
                db.commit()
                db.refresh(obj)
                break
