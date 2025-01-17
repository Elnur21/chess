from game import GameManager, GameBoard
from database import DatabaseManager


if __name__ == "__main__":
    HOST = '127.0.0.1'
    PORT = 8080
    db_manager = DatabaseManager("", "","","")
    game_board = GameBoard()
    game_manager = GameManager()
    game = game_manager.create_game(HOST, PORT, db_manager, game_board)
    game.launch_game()
    game.display_turn_history()