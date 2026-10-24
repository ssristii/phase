"""In-memory MongoDB-like store for local development without a database.

This is a fallback only. Data is lost when the Streamlit process exits. It lets
the browser prototype open and exercise the full flow without MongoDB Atlas.
"""

from __future__ import annotations

from copy import deepcopy


class MemoryCollection:
    def __init__(self):
        self.documents = []

    def create_index(self, *args, **kwargs):
        return None

    def insert_one(self, document):
        self.documents.append(deepcopy(document))

    def find(self, query=None, projection=None):
        query = query or {}
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

    def find_one(self, query=None):
        query = query or {}
        for document in self.documents:
            if all(document.get(key) == value for key, value in query.items()):
                return deepcopy(document)
        return None

    def replace_one(self, query, replacement, upsert=False):
        query = query or {}
        for index, document in enumerate(self.documents):
            if all(document.get(key) == value for key, value in query.items()):
                self.documents[index] = deepcopy(replacement)
                return
        if upsert:
            self.documents.append(deepcopy(replacement))

    def update_one(self, query, update, upsert=False):
        query = query or {}
        index = None
        for i, document in enumerate(self.documents):
            if all(document.get(key) == value for key, value in query.items()):
                index = i
                break
        if index is None:
            if not upsert:
                return
            document = dict(query)
            self.documents.append(document)
            index = len(self.documents) - 1
        document = self.documents[index]
        if "$set" in (update or {}):
            document.update(deepcopy(update["$set"]))
        if "$setOnInsert" in (update or {}):
            for key, value in update["$setOnInsert"].items():
                document.setdefault(key, deepcopy(value))

    def update_many(self, query, update):
        query = query or {}
        for document in self.documents:
            if all(document.get(key) == value for key, value in query.items()):
                document.update(deepcopy((update or {}).get("$set", {})))

    def count_documents(self, query=None):
        query = query or {}
        return sum(
            1
            for document in self.documents
            if all(document.get(key) == value for key, value in query.items())
        )

    def distinct(self, field, query=None):
        query = query or {}
        return list(
            {
                document[field]
                for document in self.documents
                if field in document
                and all(document.get(key) == value for key, value in query.items())
            }
        )

    def delete_one(self, query=None):
        query = query or {}
        for index, document in enumerate(self.documents):
            if all(document.get(key) == value for key, value in query.items()):
                del self.documents[index]
                return


class InMemoryDatabase:
    def __init__(self, name="phase"):
        self.name = name
        self.accounts = MemoryCollection()
        self.checkins = MemoryCollection()
        self.phase_hearts = MemoryCollection()
        self.phase_locks = MemoryCollection()
        self.model_weights = MemoryCollection()

    def __getitem__(self, name):
        if not hasattr(self, name):
            setattr(self, name, MemoryCollection())
        return getattr(self, name)


def connect_in_memory(database_name="phase"):
    return InMemoryDatabase(database_name)
