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
    get_readiness_weights,
    hash_login_code,
    list_checkins,
    lock_phase_plan,
    reset_readiness_weights,
    save_checkin,
    save_phase_workout_plan,
    save_readiness_weights,
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

    def update_many(self, query, update):
        for document in self.documents:
            if all(document.get(key) == value for key, value in query.items()):
                document.update(deepcopy(update.get("$set", {})))

    def count_documents(self, query):
        return sum(
            1
            for document in self.documents
            if all(document.get(key) == value for key, value in query.items())
        )

    def distinct(self, field, query):
        return list(
            {
                document[field]
                for document in self.documents
                if field in document
                and all(document.get(key) == value for key, value in query.items())
            }
        )

    def delete_one(self, query):
        for index, document in enumerate(self.documents):
            if all(document.get(key) == value for key, value in query.items()):
                del self.documents[index]
                return


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
        for phase in ("Menstrual", "Follicular", "Ovulatory", "Luteal"):
            add_phase_heart(hearts, "account-1", phase)
        add_phase_heart(hearts, "account-1", "Luteal")
        self.assertEqual(count_phase_hearts(hearts, "account-1"), 4)

        save_phase_workout_plan(
            locks,
            "account-1",
            "Luteal",
            [{"title": "Gentle strength"}],
        )
        self.assertIsNone(get_phase_lock(locks, "account-1", "Luteal"))
        lock_phase_plan(locks, "account-1")
        self.assertEqual(
            get_phase_lock(locks, "account-1", "Luteal")["workout_plan"][0]["title"],
            "Gentle strength",
        )

    def test_unsure_profile_stores_no_period_date(self):
        profile = stored_profile(
            {
                "cycle_tracking_mode": "unsure",
                "last_period": date(2026, 10, 24),
                "goal": "Strength",
                "workouts_per_week": 3,
                "usual_split": "Full body",
            }
        )
        self.assertTrue(profile["cycle_date_unsure"])
        self.assertIsNone(profile["last_period_start"])
        self.assertEqual(
            set(profile),
            {
                "version",
                "cycle_tracking_mode",
                "cycle_date_unsure",
                "last_period_start",
                "cycle_length",
                "goal",
                "workouts_per_week",
                "usual_split",
            },
        )

    def test_profile_stores_only_the_selected_setup_fields(self):
        profile = stored_profile(
            {
                "cycle_tracking_mode": "period_date",
                "last_period": date(2026, 10, 1),
                "goal": "Endurance",
                "workouts_per_week": 5,
                "usual_split": "Push/Pull/Legs",
            }
        )

        self.assertEqual(profile["version"], 2)
        self.assertEqual(profile["last_period_start"], "2026-10-01")
        self.assertEqual(profile["workouts_per_week"], 5)
        self.assertEqual(profile["usual_split"], "Push/Pull/Legs")
        self.assertEqual(profile["goal"], "Endurance")

    def test_contraception_profile_uses_symptom_mode_without_storing_a_date(self):
        profile = stored_profile(
            {
                "cycle_tracking_mode": "hormonal_contraception",
                "last_period": date(2026, 10, 1),
                "goal": "General fitness",
                "workouts_per_week": 2,
                "usual_split": "Not sure",
            }
        )

        self.assertTrue(profile["cycle_date_unsure"])
        self.assertIsNone(profile["last_period_start"])
        self.assertEqual(
            profile["cycle_tracking_mode"],
            "hormonal_contraception",
        )

    def test_profile_rejects_workout_frequency_outside_one_to_seven(self):
        with self.assertRaises(ValueError):
            stored_profile(
                {
                    "cycle_tracking_mode": "unsure",
                    "last_period": None,
                    "goal": "Strength",
                    "workouts_per_week": 8,
                    "usual_split": "Full body",
                }
            )

    def test_period_date_mode_requires_a_date(self):
        with self.assertRaises(ValueError):
            stored_profile(
                {
                    "cycle_tracking_mode": "period_date",
                    "last_period": None,
                    "goal": "Strength",
                    "workouts_per_week": 3,
                    "usual_split": "Full body",
                }
            )

    def test_readiness_weights_are_versioned_per_account(self):
        weights_store = MemoryCollection()
        save_readiness_weights(
            weights_store,
            "account-1",
            [0.1] * 9,
            version=1,
        )
        loaded = get_readiness_weights(weights_store, "account-1")
        self.assertEqual(loaded, [0.1] * 9)
        self.assertIsNone(get_readiness_weights(weights_store, "account-2"))
        reset_readiness_weights(weights_store, "account-1")
        self.assertIsNone(get_readiness_weights(weights_store, "account-1"))

    def test_list_checkins_orders_by_date(self):
        checkins = MemoryCollection()
        values = {
            "flow": "None",
            "mood": "Okay",
            "energy": 3,
            "sleep_hours": 7,
            "pain": 0,
            "workout_done": False,
            "severe_pain": False,
            "irregular": False,
            "pregnancy": False,
        }
        save_checkin(checkins, "account-1", values, date(2026, 10, 24))
        save_checkin(checkins, "account-1", values, date(2026, 10, 20))
        ordered = list_checkins(checkins, "account-1")
        self.assertEqual(
            [item["checkin_date"] for item in ordered],
            ["2026-10-20", "2026-10-24"],
        )


if __name__ == "__main__":
    unittest.main()
