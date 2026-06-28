import json
import os
from types import SimpleNamespace

try:
    import pyodbc
except ImportError:  # pragma: no cover - handled in environments without pyodbc
    pyodbc = None


class DatabaseError(Exception):
    pass


class JsonFallbackConnection:
    def __init__(self, data_file):
        self.data_file = data_file
        self._ensure_storage()

    def _ensure_storage(self):
        directory = os.path.dirname(self.data_file)
        if directory:
            os.makedirs(directory, exist_ok=True)

        if not os.path.exists(self.data_file):
            self._data = {"Users": [], "Games": [], "Moves": []}
            self._save_data()
        else:
            self._data = self._load_data()

    def _load_data(self):
        try:
            with open(self.data_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return {
                "Users": data.get("Users", []),
                "Games": data.get("Games", []),
                "Moves": data.get("Moves", []),
            }
        except (json.JSONDecodeError, OSError):
            return {"Users": [], "Games": [], "Moves": []}

    def _save_data(self):
        with open(self.data_file, "w", encoding="utf-8") as handle:
            json.dump(self._data, handle, indent=2)

    def cursor(self):
        return JsonFallbackCursor(self)

    def commit(self):
        self._save_data()


class JsonFallbackCursor:
    def __init__(self, connection):
        self.connection = connection
        self._result = []

    def execute(self, query, params=None):
        params = params or ()
        normalized_query = " ".join(query.split()).strip().upper()

        if normalized_query.startswith("SELECT USERNAME, POINTS FROM USERS ORDER BY POINTS DESC"):
            users = sorted(self.connection._data.get("Users", []), key=lambda user: user.get("Points", 0), reverse=True)
            self._result = [(user.get("Username"), user.get("Points")) for user in users]
            return self

        if normalized_query.startswith("SELECT * FROM USERS WHERE USERNAME ="):
            username = params[0]
            user = next((user for user in self.connection._data.get("Users", []) if user.get("Username") == username), None)
            self._result = [SimpleNamespace(**user)] if user else []
            return self

        if normalized_query.startswith("SELECT MOVE FROM MOVES WHERE GAMEID ="):
            game_id = str(params[0])
            moves = [move.get("Move") for move in self.connection._data.get("Moves", []) if str(move.get("GameID")) == game_id]
            self._result = [(move,) for move in moves]
            return self

        if normalized_query.startswith("INSERT INTO USERS"):
            username, points = params
            if not any(user.get("Username") == username for user in self.connection._data.get("Users", [])):
                self.connection._data["Users"].append({"Username": username, "Points": points})
            self._result = []
            return self

        if normalized_query.startswith("UPDATE USERS SET POINTS ="):
            points, username = params
            for user in self.connection._data.get("Users", []):
                if user.get("Username") == username:
                    user["Points"] = points
                    break
            self._result = []
            return self

        if normalized_query.startswith("INSERT INTO GAMES"):
            game_id = str(params[0]) if params else None
            if game_id and not any(game.get("ID") == game_id for game in self.connection._data.get("Games", [])):
                self.connection._data["Games"].append({"ID": game_id})
            self._result = []
            return self

        if normalized_query.startswith("INSERT INTO MOVES"):
            game_id, move = params
            self.connection._data["Moves"].append({"GameID": str(game_id), "Move": move})
            self._result = []
            return self

        raise self._database_error(f"Unsupported fallback query: {query}")

    def fetchone(self):
        return self._result[0] if self._result else None

    def fetchall(self):
        return list(self._result)

    def close(self):
        return None

    def _database_error(self, message):
        if pyodbc is not None:
            return pyodbc.Error(message)
        return DatabaseError(message)


class DatabaseManager:
    DRIVER = "ODBC Driver 17 for SQL Server"
    TRUSTED_CONNECTION = "yes"

    def __init__(self, server, database, username, password):
        self.db_server = server
        self.db_database = database
        self.db_username = username
        self.db_password = password
        self.json_file = os.path.join(os.path.dirname(__file__), "chess_data.json")
        self.db_connection = self.create_db_connection(self.db_server, self.TRUSTED_CONNECTION)
        self.master_db_connection = self.create_db_connection(self.db_server, self.TRUSTED_CONNECTION)
        self.create_database_if_not_exists()
        self.create_table_if_not_exists()
        self.create_games_table_if_not_exists()
        self.create_turns_table_if_not_exists()

    def create_db_connection(self, server, trusted_conn):
        if pyodbc is None:
            print("pyodbc is not available; using JSON fallback storage.")
            return JsonFallbackConnection(self.json_file)

        try:
            return pyodbc.connect(
                f"DRIVER={self.DRIVER};"
                f"SERVER={server};"
                f"DATABASE={self.db_database};"
            )
        except Exception as exc:
            print(f"Database unavailable, using JSON fallback storage: {exc}")
            return JsonFallbackConnection(self.json_file)

    def create_database_if_not_exists(self):
        try:
            if isinstance(self.master_db_connection, JsonFallbackConnection):
                self.master_db_connection.commit()
                return

            cursor = self.master_db_connection.cursor()
            cursor.execute(f"SELECT * FROM sys.databases WHERE name = '{self.db_database}'")
            database_exists = cursor.fetchone()
            if not database_exists:
                cursor.execute(f"CREATE DATABASE {self.db_database}")
                self.master_db_connection.commit()
            cursor.close()
        except Exception as exc:
            print(f"Error creating/checking database: {str(exc)}")

    def create_table_if_not_exists(self):
        try:
            if isinstance(self.db_connection, JsonFallbackConnection):
                self.db_connection.commit()
                return

            cursor = self.db_connection.cursor()
            cursor.execute(
                f"IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Users') "
                f"CREATE TABLE Users ("
                f"ID INT IDENTITY(1,1) PRIMARY KEY,"
                f"Username VARCHAR(255),"
                f"Points INT"
                f")"
            )
            self.db_connection.commit()
            cursor.close()
        except Exception as exc:
            print(f"Error creating/checking table: {str(exc)}")

    def create_games_table_if_not_exists(self):
        try:
            if isinstance(self.db_connection, JsonFallbackConnection):
                self.db_connection.commit()
                return

            cursor = self.db_connection.cursor()
            cursor.execute(
                f"IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Games') "
                f"CREATE TABLE Games ("
                f"ID UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID()"
                f")"
            )
            self.db_connection.commit()
            cursor.close()
        except Exception as exc:
            print(f"Error creating/checking games table: {str(exc)}")

    def create_turns_table_if_not_exists(self):
        try:
            if isinstance(self.db_connection, JsonFallbackConnection):
                self.db_connection.commit()
                return

            cursor = self.db_connection.cursor()
            cursor.execute(
                f"IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Moves') "
                f"CREATE TABLE Moves ("
                f"ID INT IDENTITY(1,1) PRIMARY KEY,"
                f"GameID UNIQUEIDENTIFIER,"
                f"Move NVARCHAR(255)"
                f")"
            )
            self.db_connection.commit()
            cursor.close()
        except Exception as exc:
            print(f"Error creating/checking turns table: {str(exc)}")

