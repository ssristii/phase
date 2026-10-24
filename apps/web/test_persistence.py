import unittest
from copy import deepcopy
from datetime import date

from persistence import (
    add_phase_heart,
    authenticate_account,
    count_phase_hearts,
    create_account,
    generate_login_code,
    get_checkin,
    get_phase_lock,
    hash_login_code,
    lock_phase_plan,
    save_checkin,
    stored_profile,
)


class MemoryCollection:
    def __init__(self):
        self.documents = []

    def insert_one(self, document):
        self.documents.append(deepcopy(document))

    def find(self, query, projection=None):
        matching = [
            document
            for document in self.documents
            if all(document.get(key) == value for key, value in query.items())
        ]
        if projection:
            fields = {key for key, include in projection.items() if include}
            matching = [
                {key: value for key, value in document.items() if key in fields or key == "_id"}
                for document in matching
            ]
        return deepcopy(matching)

    def find_one(self, query):
        for document in self.documents:
            if all(document.get(key) == value for key, value in query.items()):
                return deepcopy(document)
        return None

    def replace_one(self, query, replacement, upsert=False):
        for index, document in enumerate(self.documents):
            if all(document.get(key) == value for key, value in query.items()):
                self.documents[index] = deepcopy(replacement)
                return
        if upsert:
            self.documents.append(deepcopy(replacement))

    def update_one(self, query, update, upsert=False):
        document = self.find_one(query)
        if document is None:
            if not upsert:
                return
            document = dict(query)
            self.documents.append(document)
        if "$set" in update:
            document.update(deepcopy(update["$set"]))
        if "$setOnInsert" in update:
            for key, value in update["$setOnInsert"].items():
                document.setdefault(key, deepcopy(value))

    def count_documents(self, query):
        return sum(
            1
            for document in self.documents
            if all(document.get(key) == value for key, value in query.items())
        )


class PersistenceTests(unittest.TestCase):
    def test_generated_login_code_uses_ten_unambiguous_characters(self):
        code = generate_login_code()
        self.assertEqual(len(code), 10)
        self.assertTrue(all(character in "ABCDEFGHJKLMNPQRSTUVWXYZ23456789" for character in code))

    def test_login_code_is_stored_only_as_salted_hash(self):
        accounts = MemoryCollection()
        account_id, code = create_account(accounts, 28)
        document = accounts.find_one({"_id": account_id})

        self.assertNotIn(code, str(document))
        self.assertIn("login_code_salt", document)
        self.assertEqual(
            document["login_code_hash"],
            hash_login_code(code, document["login_code_salt"]),
        )
        self.assertEqual(authenticate_account(accounts, code.lower()), document)
        self.assertIsNone(authenticate_account(accounts, generate_login_code()))

    def test_minors_cannot_create_accounts(self):
        with self.assertRaises(ValueError):
            create_account(MemoryCollection(), 17)

    def test_checkin_is_upserted_for_account_and_date(self):
        checkins = MemoryCollection()
        values = {
            "flow": "Light",
            "mood": "Okay",
            "energy": 3,
            "sleep_hours": 7,
            "pain": 2,
            "workout_done": False,
            "severe_pain": False,
            "irregular": False,
            "pregnancy": False,
        }
        save_checkin(checkins, "account-1", values, date(2026, 10, 24))
        values["pain"] = 4
        save_checkin(checkins, "account-1", values, date(2026, 10, 24))

        result = get_checkin(checkins, "account-1", date(2026, 10, 24))
        self.assertEqual(result["pain"], 4)
        self.assertEqual(len(checkins.documents), 1)

    def test_four_phase_hearts_can_lock_a_phase_keyed_plan(self):
        hearts = MemoryCollection()
        locks = MemoryCollection()
        for week in range(1, 5):
            add_phase_heart(hearts, "account-1", "Luteal", "workout", week)
        add_phase_heart(hearts, "account-1", "Luteal", "workout", 1)
        self.assertEqual(count_phase_hearts(hearts, "account-1", "Luteal"), 4)

        lock_phase_plan(
            locks,
            "account-1",
            "Luteal",
            {"title": "Gentle strength"},
            ["Beans", "Sweet potatoes"],
        )
        self.assertEqual(
            get_phase_lock(locks, "account-1", "Luteal")["workout_plan"]["title"],
            "Gentle strength",
        )

    def test_unsure_profile_stores_no_period_date(self):
        profile = stored_profile(
            {
                "unsure": True,
                "last_period": date(2026, 10, 24),
                "cycle_length": None,
                "goal": "Strength",
                "exercises": [],
                "diet": "No preference",
            }
        )
        self.assertTrue(profile["cycle_date_unsure"])
        self.assertIsNone(profile["last_period_start"])


if __name__ == "__main__":
    unittest.main()
