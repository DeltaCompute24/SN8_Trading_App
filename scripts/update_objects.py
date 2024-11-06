from src.database_tasks import TaskSessionLocal_
from src.models import Challenge


# write a function to populate challenge_name field in the Challenge model by challenge.user.username_challenge.id
def populate_challenge_name():
    with TaskSessionLocal_() as db:
        challenges = db.query(Challenge).all()
        for challenge in challenges:
            username = challenge.user.username
            if not username:
                print(f"Username not found for challenge: {challenge.id} - {challenge.user_id}")
                continue
            challenge_name = f"{username}_{challenge.id}"
            challenge.challenge_name = challenge_name
        db.commit()
