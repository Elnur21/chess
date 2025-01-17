import chess
import tkinter as tk
from tkinter import ttk
import socket
import random
import threading
import pyodbc
import uuid
import queue

from timer import TimerManager

class ChessGame:
    def __init__(self, host, port, db_manager,game_board):
        self.HOST = host
        self.PORT = port
        self.db_connection = db_manager.db_connection
        self.master_db_connection = db_manager.master_db_connection

        self.game_board = game_board
        self.initialize_game()

    def initialize_game(self):
        self.piece_symbols = self.game_board.piece_symbols
        self.board = self.game_board.board
        self.score = 0
        self.client_socket = None
        self.timer_duration = 180 
        self.root = tk.Tk()
        self.root.title("Chess Game")
        self.game_mode = ""
        self.players = []
        self.move_history = []
        self.username_entry = tk.Entry(self.root)
        self.username_entry.pack()
        self.username_entry.config(state="normal")
        self.username = ""
        self.winner = ""
        self.points = 0
        self.game_id = ""
        self.square_size_y = 55
        self.square_size_x = 75
        self.player_colors = {'white': "White", 'black': "Black"}
        self.assigned_color = "white"
        self.isPlayerBlack=False
        self.first_game = True
        self.turn_history = queue.Queue()
        self.combo = ttk.Combobox(self.root)
        self.combo['values'] = ('3 min', '5 min', '10 min')
        self.combo.set('3 min')
        self.timer_manager = TimerManager()
        self.create_widgets()
        self.disable_buttons()
        self.create_leaderboard()

    def on_select_minute(self,event):
        if(self.combo.get()=="3 min"):
            self.timer_duration=3*60
        elif(self.combo.get()=="5 min"):
            self.timer_duration=5*60
        else:
            self.timer_duration=8*60

    def create_widgets(self):
        self.set_username_button = ttk.Button(self.root, text="Set Username", command=self.set_username)
        self.set_username_button.pack()
        self.connect_button = ttk.Button(self.root, text="Connect to Game", command=self.connect_to_game)
        self.connect_button.pack()
        self.minutes = tk.Label(self.root, text="Select timer:")
        self.minutes.pack()
        self.combo.bind("<<ComboboxSelected>>", self.on_select_minute)
        self.combo.pack()
        self.connect_button.config(state="disabled")
        self.canvas = tk.Canvas(self.root, width=0, height=0)
        self.canvas.pack(side="left",fill="y")
        self.undo_button = ttk.Button(self.root, text="Undo Last Move", command=self.undo_last_move)
        self.undo_button.pack()
        self.undo_button.config(state="disabled")
        self.turn_label = tk.Label(self.root, text="White's Turn", font=("Arial", 10))
        self.turn_label.pack()

        self.status_label = tk.Label(self.root, text="", font=("Arial", 10))
        self.status_label.pack()

        self.stop_game_button = ttk.Button(self.root, text="Stop game", command=lambda: self.stop_game())
        self.stop_game_button.pack()
        self.stop_game_button.config(state="disabled")

        level_label = tk.Label(self.root, text="Choose AI level:")
        level_label.pack()

        self.level_var = tk.StringVar()
        self.level_var.set("easy")

        self.easy_radio = tk.Radiobutton(self.root, text="Easy", variable=self.level_var, value="easy")
        self.easy_radio.pack()
        self.medium_radio = tk.Radiobutton(self.root, text="Medium", variable=self.level_var, value="medium")
        self.medium_radio.pack()
        self.hard_radio = tk.Radiobutton(self.root, text="Hard", variable=self.level_var, value="hard")
        self.hard_radio.pack()

        self.single_player_button = ttk.Button(self.root, text="Start Single Player", command=self.single_player)
        self.single_player_button.pack()

        self.multi_player_button = ttk.Button(self.root, text="Start Multi Player", command=self.multi_player)
        self.multi_player_button.pack()

        self.canvas.bind("<Button-1>", self.on_square_click)
        self.selected_square = None

    def create_leaderboard(self):
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT Username, Points FROM Users ORDER BY Points DESC")
            leaderboard_data = cursor.fetchall()

            leaderboard_frame = ttk.Frame(self.root)
            leaderboard_frame.pack(side="right", padx=10, pady=10, fill="y")

            self.leaderboard_label = ttk.Label(leaderboard_frame, text="Leaderboard", font=("Helvetica", 16, "bold"))
            self.leaderboard_label.pack(side="top", pady=(0, 10))

            style = ttk.Style()
            style.configure("Treeview", font=("Helvetica", 12))
            style.configure("Treeview.Heading", font=("Helvetica", 14, "bold"))

            self.leaderboard_table = ttk.Treeview(leaderboard_frame, columns=("Username", "Points"), show="headings")
            self.leaderboard_table.heading("Username", text="Username")
            self.leaderboard_table.heading("Points", text="Points")

            for row in leaderboard_data:
                self.leaderboard_table.insert("", "end", values= [row[0],row[1]])

            scrollbar = ttk.Scrollbar(leaderboard_frame, orient="vertical", command=self.leaderboard_table.yview)
            self.leaderboard_table.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side="right", fill="y")

            self.leaderboard_table.pack(fill="both", expand=True)
        except pyodbc.Error as e:
            print(f"Error fetching leaderboard data: {str(e)}")

    def reload_leaderboard(self):
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT Username, Points FROM Users ORDER BY Points DESC")
            leaderboard_data = cursor.fetchall()

            for item in self.leaderboard_table.get_children():
                self.leaderboard_table.delete(item)

            for row in leaderboard_data:
                self.leaderboard_table.insert("", "end", values=[row[0], row[1]])

        except pyodbc.Error as e:
            print(f"Error fetching leaderboard data: {str(e)}")

    def set_username(self):
        cursor = self.db_connection.cursor()
        self.username = self.username_entry.get()
        cursor.execute("SELECT * FROM Users WHERE Username = ?", (self.username,))
        existing_user = cursor.fetchone()

        if existing_user:
            print(f"Welcome back, {self.username}!")
            self.points = existing_user.Points
        else:
            cursor.execute("INSERT INTO Users (Username, Points) VALUES (?, ?)", (self.username, 0))
            print(f"Welcome, {self.username}!")
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
        self.isPlayerBlack = self.assigned_color == "black"
        self.status_label.config(text=f"You are playing as {self.player_colors[self.assigned_color]}.")
        self.game_board.update_board(self.canvas, self.isPlayerBlack)
        receive_thread = threading.Thread(target=self.receive_moves)
        receive_thread.start()

    def enable_buttons(self):
        self.single_player_button.config(state="normal")
        self.multi_player_button.config(state="normal")
        self.easy_radio.config(state="normal")
        self.medium_radio.config(state="normal")
        self.hard_radio.config(state="normal")
        self.canvas.config(state="normal")

    def check_win(self):
        if(self.game_mode=="multi"):
            self.timer_manager.timer_pause=False
        if self.board.is_checkmate():
            if self.board.turn == chess.WHITE:
                self.winner = "Black"
            else: 
                self.winner = "White"
            self.status_label.config(text=f"Congratulation! {self.winner} wins!")
            self.points+=1
            self.update_user_points(self.username, self.points)
            self.disable_buttons()
            self.timer_manager.timer_running = False
            return True
        elif self.board.is_stalemate():
            self.status_label.config(text="")
            self.disable_buttons()
            self.timer_manager.timer_running = False
            return True
        return False

    def update_user_points(self, username, points):
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("UPDATE Users SET Points = ? WHERE Username = ?", (points, username))
            self.db_connection.commit()
            cursor.close()
        except pyodbc.Error as e:
            print(f"Error updating user points: {str(e)}")

    def fetch_and_display_moves(self, game_id):
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT Move FROM Moves WHERE GameID = ?", (str(game_id),))
            moves_data = cursor.fetchall()

            if self.first_game == True:
                moves_frame = ttk.Frame(self.root)
                moves_frame.pack(side="right", padx=10, pady=10, fill="y")

                self.moves_label = ttk.Label(moves_frame, text="Moves", font=("Helvetica", 16, "bold"))
                self.moves_label.pack(side="top", pady=(0, 10))

                self.moves_listbox = tk.Listbox(moves_frame, font=("Helvetica", 12), selectmode="browse")
                self.moves_listbox.pack(fill="both", expand=True)
                self.first_game=False
            else:
                self.moves_listbox.delete(0, tk.END)

            for move in moves_data:
                self.moves_listbox.insert("start", move[0])

        except pyodbc.Error as e:
            print(f"Error fetching moves data: {str(e)}")

    def display_turn_history(self):
        while not self.turn_history.empty():
            move = self.turn_history.get()
            print(f"Move: {move.uci()}")
        

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
                self.game_board.update_board(self.canvas, self.isPlayerBlack)
                self.timer_manager.timer_pause == False
                if self.check_win():
                    break
                
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
        self.record_turn(self.game_id, move)
        self.board.push(move)
        if self.game_mode !="single":
            self.timer_manager.timer_pause=True
            
        self.move_history.append(move)

        self.game_board.update_board(self.canvas, self.isPlayerBlack)

        if self.check_win():
            self.create_leaderboard()
            self.moves_label.pack_forget()
            self.moves_listbox.pack_forget()
            self.undo_button.config(state="disabled")
            self.canvas.config(width=0, height=0)
            return

        if self.game_mode == "single":
            self.turn_label.config(text="Black's Turn" if self.board.turn == chess.BLACK else "White's Turn")
            random_number = random.randint(1, 4)
            threading.Timer(random_number, self.ai_move, args=(self.level_var.get(),)).start()
        if self.game_mode == "multi":
            self.turn_label.config(text="Black's Turn" if self.board.turn == chess.BLACK else "White's Turn")
            self.timer_manager.timer_pause=True
            
        else:
            self.turn_label.config(text="Black's Turn" if self.board.turn == chess.BLACK else "White's Turn")

    def undo_last_move(self):
        if self.move_history:
            last_move = self.move_history.pop()
            self.board.pop()
            self.game_board.update_board(self.canvas, self.isPlayerBlack)
            self.status_label.config(text=f"Last move undone: {last_move.uci()}")
        else:
            self.status_label.config(text="No move to undo.")

    def easy_ai_move(self):
        legal_moves = list(self.board.legal_moves)
        ai_move = random.choice(legal_moves)
        return ai_move

    def ai_move(self, level):
        self.game_board.update_board(self.canvas, self.isPlayerBlack)
        if level == "easy":
            move = self.easy_ai_move()
        elif level == "medium":
            move = self.find_best_move(self.board, depth=3)
        elif level == "hard":
            move = self.find_best_move(self.board, depth=5)
        self.board.push(move)
        self.game_board.update_board(self.canvas, self.isPlayerBlack)

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

    def stop_game(self):
        self.single_player_button.config(state="normal")
        self.multi_player_button.config(state="normal")
        self.timer_manager.stop_timer()
        self.stop_game_button.config(state="disabled")

    def new_game(self):
        self.timer_manager.set_parameters(self.board, self.minutes, self.game_mode, self.points, self.combo, self.username, self.status_label, self.canvas)
        minutes, seconds = divmod(self.timer_duration, 60)
        timer_str = '{:02d}:{:02d}'.format(minutes, seconds)
        self.minutes.configure(text=timer_str)

        if(self.game_mode=="single"):
            self.timer_manager.start_timer(self.timer_duration)
            self.timer_manager.timer_pause=False
            
        self.combo.config(state="disabled")
        self.leaderboard_table.pack_forget()
        self.leaderboard_label.pack_forget()
        self.canvas.config(width=600, height=400)
        self.undo_button.config(state="disabled")
        self.create_new_game()
        self.reload_leaderboard()
        self.fetch_and_display_moves(self.game_id)
        self.board.set_fen(chess.STARTING_FEN)
        self.enable_buttons()
        self.game_board.update_board(self.canvas, self.isPlayerBlack)
        self.status_label.config(text="New game started.")
        self.single_player_button.config(state="disabled")
        self.multi_player_button.config(state="disabled")
        self.stop_game_button.config(state="normal")

    def single_player(self):
        self.game_mode = "single"
        self.enable_buttons()
        level = self.level_var.get()
        self.new_game()
        random_number = random.randint(0, 1)
        if(random_number == 1):
            self.isPlayerBlack = True
            self.game_board.update_board(self.canvas, self.isPlayerBlack)
            random_number = random.randint(1, 4)
            threading.Timer(random_number, self.ai_move, args=(level,)).start()
            
        else:
            self.isPlayerBlack = False
            self.game_board.update_board(self.canvas, self.isPlayerBlack)
        self.status_label.config(text="Single-player game started. You are playing as Black.")

    def create_new_game(self):
        game_id = uuid.uuid4()  # Generate a unique game ID
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("INSERT INTO Games (ID) VALUES (?)", (str(game_id),))
            self.db_connection.commit()
            cursor.close()
            self.game_id=game_id
            return game_id
        except pyodbc.Error as e:
            print(f"Error creating a new game: {str(e)}")
            return None

    def record_turn(self, game_id, move):
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("INSERT INTO Moves (GameID, Move) VALUES (?, ?)", (str(game_id), f"{move.uci()[0:2]}=>{move.uci()[2:4]} {self.piece_symbols[self.board.piece_at(move.from_square).symbol()]} {'white' if self.board.piece_at(move.from_square).color == chess.WHITE else 'black'}"))
            self.db_connection.commit()
            self.turn_history.put(move)
            self.moves_listbox.delete(0, tk.END)
            cursor.execute("SELECT Move FROM Moves WHERE GameID = ?", (str(game_id),))
            moves_data = cursor.fetchall()
            self.moves_listbox.config(justify="center")
            for data in moves_data:
                self.moves_listbox.insert("end", data[0])

            cursor.close()
        except pyodbc.Error as e:
            print(f"Error recording a turn: {str(e)}")

    def multi_player(self):
        self.new_game()
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.game_mode = "multi"
        self.username_entry.config(state="normal")
        self.connect_button.config(state="normal")
        self.disable_buttons()
        self.status_label.config(text="Multi-player game started. You are playing as White.")
        self.timer_manager.timer_pause=True
        self.timer_manager.start_timer(self.timer_duration)

        try:
            self.players.append(self.username)
            player_list = ",".join(self.players)
            self.client_socket.send(player_list.encode())
            
        except Exception as e:
            print(f"Error starting a multiplayer game: {str(e)}")

    def disable_buttons(self):
        self.single_player_button.config(state="disabled")
        self.multi_player_button.config(state="disabled")
        self.easy_radio.config(state="disabled")
        self.medium_radio.config(state="disabled")
        self.hard_radio.config(state="disabled")
        self.canvas.delete("all")
        self.timer_manager.timer_running=False

    def on_square_click(self, event):
        self.easy_radio.config(state="disabled")
        self.medium_radio.config(state="disabled")
        self.hard_radio.config(state="disabled")
        if self.game_mode == "single":
            self.undo_button.config(state="normal")
        if(self.game_mode == "multi"):
            self.timer_manager.timer_pause=False

        x, y = event.x, event.y
        col = x // self.square_size_x
        row = y // self.square_size_y
        square = chess.square(col, 7 - row)
        if self.isPlayerBlack:
            square = chess.square(col, row)

        if self.selected_square is None:
            piece = self.board.piece_at(square)
            if piece is not None and piece.color == self.board.turn:
                self.selected_square = square
                self.possible_moves = list(self.board.legal_moves)
                self.game_board.update_board(self.canvas, self.isPlayerBlack)
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
        col = chess.square_file(square)
        row = 7 - chess.square_rank(square)
        if self.isPlayerBlack:
            row = chess.square_rank(square)
        x1 = col * self.square_size_x
        y1 = row * self.square_size_y
        x2 = x1 + self.square_size_x
        y2 = y1 + self.square_size_y
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


class GameBoard:
    def __init__(self):
        self.board = chess.Board()
        self.square_size_y = 55
        self.square_size_x = 75
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


    def update_board(self,canvas, isPlayerBlack):
        canvas.delete("all")
        for row in range(8):
            for col in range(8):
                x1 = col * self.square_size_x
                y1 = row * self.square_size_y
                x2 = x1 + self.square_size_x
                y2 = y1 + self.square_size_y
                color = "brown" if (row + col) % 2 == 0 else "grey"
                canvas.create_rectangle(x1, y1, x2, y2, fill=color)
                piece = self.board.piece_at(chess.square(col, 7 - row))
                if isPlayerBlack:
                    piece = self.board.piece_at(chess.square(col, row))
                if piece is not None:
                    symbol = self.piece_symbols[piece.symbol()]
                    figColor = "white" if piece.color == chess.WHITE else "black"
                    canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=symbol, font=("Courier", 24),
                                            fill=figColor)
        canvas.update()

class GameManager:
    def __init__(self):
        self.games = []

    def create_game(self, host, port, db_manager, game_board):
        game = ChessGame(host, port, db_manager, game_board)
        self.games.append(game)
        return game

    def remove_game(self, game):
        self.games.remove(game)