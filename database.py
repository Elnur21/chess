import pyodbc

class DatabaseManager:
    DRIVER = "ODBC Driver 17 for SQL Server"
    TRUSTED_CONNECTION = "yes"

    def __init__(self, server, database,username,password):
        self.db_server = server
        self.db_database = database
        self.db_username = username
        self.db_password = password
        self.db_connection = self.create_db_connection(self.db_server, self.TRUSTED_CONNECTION)
        self.master_db_connection = self.create_db_connection(self.db_server, self.TRUSTED_CONNECTION)
        self.create_database_if_not_exists()
        self.create_table_if_not_exists()
        self.create_games_table_if_not_exists()
        self.create_turns_table_if_not_exists()


    def create_db_connection(self, server, trusted_conn):
        return pyodbc.connect(
            f"DRIVER={self.DRIVER};"
            f"SERVER={server};"
            f"DATABASE={self.db_database};"
        )

    def create_database_if_not_exists(self):
        try:
            cursor = self.master_db_connection.cursor()
            cursor.execute(f"SELECT * FROM sys.databases WHERE name = '{self.db_database}'")
            database_exists = cursor.fetchone()
            if not database_exists:
                cursor.execute(f"CREATE DATABASE {self.db_database}")
                self.master_db_connection.commit()
            cursor.close()
        except pyodbc.Error as e:
            print(f"Error creating/checking database: {str(e)}")

    def create_table_if_not_exists(self):
        try:
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
        except pyodbc.Error as e:
            print(f"Error creating/checking table: {str(e)}")

    def create_games_table_if_not_exists(self):
        try:
            cursor = self.db_connection.cursor()
            cursor.execute(
                f"IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Games') "
                f"CREATE TABLE Games ("
                f"ID UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID()"
                f")"
            )
            self.db_connection.commit()
            cursor.close()
        except pyodbc.Error as e:
            print(f"Error creating/checking games table: {str(e)}")

    def create_turns_table_if_not_exists(self):
        try:
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
        except pyodbc.Error as e:
            print(f"Error creating/checking turns table: {str(e)}")

