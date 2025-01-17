import chess
import random
import chess.engine
import tkinter as tk
from tkinter import ttk
import socket
import threading
import pyodbc

class ChessGame:
    def __init__(self, host, port):
        self.db_server = ''
        self.db_database = ''
        self.db_username = ''
        self.db_password = ''

        self.db_connection = pyodbc.connect(
            f"DRIVER=ODBC Driver 17 for SQL Server;"
            f"SERVER={self.db_server};"
            f"DATABASE={self.db_database};"
            f"UID={self.db_username};"
            f"PWD={self.db_password};"
        )
        self.master_db_connection = pyodbc.connect(
            f"DRIVER=ODBC Driver 17 for SQL Server;"
            f"SERVER={self.db_server};"
            f"UID={self.db_username};"
            f"PWD={self.db_password};"
        )

        self.create_database_if_not_exists()
        self.create_table_if_not_exists()
        self.HOST = host
        self.PORT = port
        self.client_socket = None
        self.board = chess.Board()
        self.root = tk.Tk()
        self.root.title("Chess Game")
        self.game_mode = ""
        self.players = []
        self.username_entry = tk.Entry(self.root)
        self.username_entry.pack()
        self.username_entry.config(state="normal")
        self.username = ""
        self.winner=""
        self.points=0
        self.player_colors = {
            'white': "White",
            'black': "Black",
        }
        self.assigned_color = "white"
        self.create_widgets()
        self.disable_buttons()
        

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

    def create_widgets(self):
        self.set_username_button = ttk.Button(self.root, text="Set Username", command=self.set_username)
        self.set_username_button.pack()
        self.connect_button = ttk.Button(self.root, text="Connect to Game", command=self.connect_to_game)
        self.connect_button.pack()
        self.connect_button.config(state="disabled")
        self.piece_symbols = {
            'P': '♟',
            'N': '♞',
            'B': '♝',
            'R': '♜',
            'Q': '♛',
            'K': '♚',
            'p': '♟',
            'n': '♞',
            'b': '♝',
            'r': '♜',
            'q': '♛',
            'k': '♚',
        }
        self.canvas = tk.Canvas(self.root, width=600, height=400)
        self.canvas.pack()
        self.turn_label = tk.Label(self.root, text="White's Turn", font=("Arial", 10))
        self.turn_label.pack()

        self.status_label = tk.Label(self.root, text="", font=("Arial", 10))
        self.status_label.pack()

        self.new_game_button = ttk.Button(self.root, text="New Game", command=lambda: self.new_game())
        self.new_game_button.pack()

        level_label = tk.Label(self.root, text="Choose AI level:")
        level_label.pack()

        self.level_var = tk.StringVar()
        self.level_var.set("easy")

        self.easy_radio = tk.Radiobutton(self.root, text="Easy", variable=self.level_var, value="easy")
        self.easy_radio.pack()
        self.hard_radio = tk.Radiobutton(self.root, text="Hard", variable=self.level_var, value="hard")
        self.hard_radio.pack()

        self.single_player_button = ttk.Button(self.root, text="Start Single Player", command=self.single_player)
        self.single_player_button.pack()

        self.multi_player_button = ttk.Button(self.root, text="Start Multi Player", command=self.multi_player)
        self.multi_player_button.pack()

        self.canvas.bind("<Button-1>", self.on_square_click)
        self.selected_square = None

    def launch_game(self):
        self.root.mainloop()


    def set_username(self):
        cursor = self.db_connection.cursor()
        self.username = self.username_entry.get()
        cursor.execute("INSERT INTO Users (Username, Points) VALUES (?, ?)", (self.username,0))
        self.username_entry.config(state="disabled")
        self.set_username_button.config(state="disabled")
        self.enable_buttons()

    def connect_to_game(self):
        self.username = self.username_entry.get()
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.HOST, self.PORT))
        self.username_entry.config(state="disabled")
        self.connect_button.config(state="disabled")
        self.enable_buttons()
        self.assigned_color = self.client_socket.recv(1024).decode()
        self.status_label.config(text=f"You are playing as {self.player_colors[self.assigned_color]}.")
        self.update_board()
        receive_thread = threading.Thread(target=self.receive_moves)
        receive_thread.start()

    def enable_buttons(self):
        self.single_player_button.config(state="normal")
        self.multi_player_button.config(state="normal")
        self.easy_radio.config(state="normal")
        self.hard_radio.config(state="normal")
        self.new_game_button.config(state="normal")
        self.canvas.config(state="normal")

    def check_win(self):
        if self.board.is_checkmate():
            if self.board.turn == chess.WHITE:
                self.winner = "Black"
            else:
                self.winner = "White"
            self.status_label.config(text=f"Congratulation! {self.winner} wins!")
            self.points+=1
            self.update_user_points(self.username, self.points)
            self.disable_buttons()
            return True
        elif self.board.is_stalemate():
            self.status_label.config(text="")
            self.disable_buttons()
            return True
        return False
    
    def update_user_points(self, username, points):
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("UPDATE Users SET Points = Points + ? WHERE Username = ?", (points, username))
            self.db_connection.commit()
            cursor.close()
        except pyodbc.Error as e:
            print(f"Error updating user points: {str(e)}")

    def update_board(self):
        self.canvas.delete("all")
        square_size = 50
        for row in range(8):
            for col in range(8):
                x1 = col * square_size
                y1 = row * square_size
                x2 = x1 + square_size
                y2 = y1 + square_size
                color = "brown" if (row + col) % 2 == 0 else "grey"
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color)
                piece = self.board.piece_at(chess.square(col, 7 - row))
                if piece is not None:
                    symbol = self.piece_symbols[piece.symbol()]
                    figColor = "white" if piece.color == chess.WHITE else "black"
                    self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=symbol, font=("Courier", 24),
                                            fill=figColor)
        self.canvas.update()

    def ask_for_promotion_piece(self):
        promotion_piece = None
        promotion_pieces = ['q', 'r', 'n', 'b']
        def set_promotion(piece):
            nonlocal promotion_piece
            promotion_piece = piece
            promotion_window.destroy()

        promotion_window = tk.Toplevel(self.root)
        promotion_window.title("Pawn Promotion")
        promotion_label = tk.Label(promotion_window, text="Choose a piece for promotion:")
        promotion_label.pack()

        for piece_symbol in promotion_pieces:
            button = tk.Button(
                promotion_window,
                text=self.piece_symbols[piece_symbol],
                font=("Courier", 24),
                command=lambda piece=piece_symbol: set_promotion(piece),
            )
            button.pack(side=tk.LEFT, padx=10)

        promotion_window.grab_set()
        promotion_window.wait_window()
        if str(chess.Piece.from_symbol(promotion_piece.upper())) == "Q":
            return chess.QUEEN
        elif str(chess.Piece.from_symbol(promotion_piece.upper())) == "R":
            return chess.ROOK
        elif str(chess.Piece.from_symbol(promotion_piece.upper())) == "N":
            return chess.KNIGHT
        elif str(chess.Piece.from_symbol(promotion_piece.upper())) == "B":
            return chess.BISHOP

    def send_move(self, move):
        self.client_socket.send(move.uci().encode())

    def receive_moves(self):
        while True:
            try:
                move_uci = self.client_socket.recv(1024).decode()
                move = chess.Move.from_uci(move_uci)
                self.board.push(move)
                self.update_board()
                self.turn_label.config(
                    text=f"{self.username}'s Turn" if self.board.turn == chess.BLACK else f"{self.username}'s Turn")

            except Exception as e:
                print(e)
                break

    def player_move(self, move):
        if self.board.piece_at(move.from_square).color == chess.WHITE and (
                self.board.piece_at(move.from_square).piece_type == chess.PAWN and chess.square_rank(
            move.to_square) in [7, 7]):
            promotion_piece = self.ask_for_promotion_piece()
            move.promotion = promotion_piece
        if self.board.piece_at(move.from_square).color == chess.BLACK and (
                self.board.piece_at(move.from_square).piece_type == chess.PAWN and chess.square_rank(
            move.to_square) in [0, 7]):
            promotion_piece = self.ask_for_promotion_piece()
            move.promotion = promotion_piece

        if self.game_mode == "multi":
            self.send_move(move)
        self.board.push(move)
        self.update_board()

        if self.check_win():
            self.new_game_button.config(state="normal")
            return 

        if self.game_mode == "single":
            self.ai_move(self.level_var.get())
        if self.game_mode == "multi":
            self.turn_label.config(text="Black's Turn" if self.board.turn == chess.BLACK else "White's Turn")
        else:
            self.turn_label.config(text="Black's Turn" if self.board.turn == chess.BLACK else "White's Turn")

    def easy_ai_move(self):
        legal_moves = list(self.board.legal_moves)
        ai_move = random.choice(legal_moves)
        return ai_move

    def ai_move(self, level):
        self.update_board()
        if level == "easy":
            move = self.easy_ai_move()
        elif level == "hard":
            move = self.find_best_move(self.board, depth=5)
        self.board.push(move)
        self.update_board()

    def find_best_move(self, board, depth):
        legal_moves = list(board.legal_moves)
        best_move = None
        best_eval = -float('inf')

        for move in legal_moves:
            board.push(move)
            eval = self.minimax(board, depth - 1, -float('inf'), float('inf'), False)
            if eval > best_eval:
                best_eval = eval
                best_move = move
            board.pop()

        return best_move

    def minimax(self, board, depth, alpha, beta, maximizing_player):
        if depth == 0 or board.is_game_over():
            return self.evaluate_board(board)

        legal_moves = list(board.legal_moves)

        if maximizing_player:
            max_eval = -float('inf')
            for move in legal_moves:
                board.push(move)
                eval = self.minimax(board, depth - 1, alpha, beta, False)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                board.pop()
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float('inf')
            for move in legal_moves:
                board.push(move)
                eval = self.minimax(board, depth - 1, alpha, beta, True)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                board.pop()
                if beta <= alpha:
                    break
            return min_eval

    def evaluate_board(self, board):
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
        }

        evaluation = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece is not None:
                if piece.color == chess.WHITE:
                    evaluation += piece_values.get(piece.piece_type, 0)
                else:
                    evaluation -= piece_values.get(piece.piece_type, 0)

        return evaluation

    def new_game(self):
        self.board.set_fen(chess.STARTING_FEN)
        self.enable_buttons()
        self.update_board()
        self.status_label.config(text="New game started.")

    def single_player(self):
        self.game_mode = "single"
        self.enable_buttons()
        level = self.level_var.get()
        self.new_game()
        self.ai_move(level)
        self.status_label.config(text="Single-player game started. You are playing as Black.")

    def multi_player(self):
        self.new_game()
        self.game_mode = "multi"
        self.username_entry.config(state="normal")
        self.connect_button.config(state="normal")
        self.disable_buttons()
        self.status_label.config(text="Multi-player game started. You are playing as White.")

        try:
            self.players.append(self.username)
            player_list = ",".join(self.players)
            self.client_socket.send(player_list.encode())
        except:
            pass

    def disable_buttons(self):
        self.single_player_button.config(state="disabled")
        self.multi_player_button.config(state="disabled")
        self.easy_radio.config(state="disabled")
        self.hard_radio.config(state="disabled")
        self.new_game_button.config(state="disabled")
        self.canvas.delete("all")

    def on_square_click(self, event):
        square_size = 50
        x, y = event.x, event.y
        col = x // square_size
        row = y // square_size
        square = chess.square(col, 7 - row)

        if self.selected_square is None:
            piece = self.board.piece_at(square)
            if piece is not None and piece.color == self.board.turn:
                self.selected_square = square
                self.possible_moves = list(self.board.legal_moves)
                self.update_board()
                self.highlight_square(square)
        else:
            move = chess.Move(self.selected_square, square)
            if (self.board.piece_at(move.from_square).color == chess.BLACK and
                    self.board.piece_at(move.from_square).piece_type == chess.PAWN and ("1" in str(move))):
                self.player_move(move)
            elif (self.board.piece_at(move.from_square).color == chess.WHITE and
                  self.board.piece_at(move.from_square).piece_type == chess.PAWN and ("8" in str(move))):
                self.player_move(move)
            elif move in self.possible_moves:
                self.player_move(move)
            self.selected_square = None

    def highlight_square(self, square):
        square_size = 50
        col = chess.square_file(square)
        row = 7 - chess.square_rank(square)
        x1 = col * square_size
        y1 = row * square_size
        x2 = x1 + square_size
        y2 = y1 + square_size
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="blue", width=3)

    def on_closing(self):
        try:
            if self.game_mode == "multi":
                self.players.remove(self.username)
                player_list = ",".join(self.players)
                self.client_socket.send(player_list.encode())
                self.client_socket.close()
        except:
            print("You didn't play a multiple game")
        self.root.destroy()

    def launch_game(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

if __name__ == "__main__":
    HOST = '127.0.0.1'
    PORT = 8080
    game = ChessGame(HOST, PORT)
    game.launch_game()
