import chess
import random
import chess.engine
import tkinter as tk
from tkinter import ttk
import socket
import threading

HOST = '127.0.0.1'
PORT = 12345

client_socket = None


board = chess.Board()

root = tk.Tk()
root.title("Chess Game")
game_mode=""

username_entry = tk.Entry(root)
username_entry.pack()
username_entry.config(state="disabled")

def connect_to_game():
    global username, client_socket
    username = username_entry.get()
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    username_entry.config(state="disabled")
    connect_button.config(state="disabled")
    new_game()
    enable_buttons()
    update_board()
    receive_thread = threading.Thread(target=receive_moves)
    receive_thread.start()


# Connect to Game button
connect_button = ttk.Button(root, text="Connect to Game", command=connect_to_game)
connect_button.pack()
connect_button.config(state="disabled")

piece_symbols = {
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

canvas = tk.Canvas(root, width=400, height=400)
canvas.pack()




def update_board():
    canvas.delete("all")
    square_size = 50
    for row in range(8):
        for col in range(8):
            x1 = col * square_size
            y1 = row * square_size
            x2 = x1 + square_size
            y2 = y1 + square_size
            color = "brown" if (row + col) % 2 == 0 else "grey"
            canvas.create_rectangle(x1, y1, x2, y2, fill=color)
            piece = board.piece_at(chess.square(col, 7 - row))
            if piece is not None:
                symbol = piece_symbols[piece.symbol()]
                figColor = "white" if piece.color == chess.WHITE else "black"
                canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=symbol, font=("Courier", 24), fill=figColor)
    canvas.update()
update_board()


def ask_for_promotion_piece():
    promotion_piece = None
    promotion_pieces = ['q', 'r', 'n', 'b']  # Queen, Rook, Knight, Bishop

    def set_promotion(piece):
        nonlocal promotion_piece
        promotion_piece = piece
        promotion_window.destroy()

    promotion_window = tk.Toplevel(root)
    promotion_window.title("Pawn Promotion")

    promotion_label = tk.Label(promotion_window, text="Choose a piece for promotion:")
    promotion_label.pack()

    for piece_symbol in promotion_pieces:
        button = tk.Button(
            promotion_window,
            text=piece_symbols[piece_symbol],
            font=("Courier", 24),
            command=lambda piece=piece_symbol: set_promotion(piece),
        )
        button.pack(side=tk.LEFT, padx=10)

    promotion_window.grab_set()  # Make the promotion window modal.
    promotion_window.wait_window()  # Wait for the player to make a choice.
    print(chess.Piece.from_symbol(promotion_piece))
    if(str(chess.Piece.from_symbol(promotion_piece.upper()))=="Q"):
        return chess.QUEEN  
    elif(str(chess.Piece.from_symbol(promotion_piece.upper()))=="R"):
        return chess.ROOK
    elif(str(chess.Piece.from_symbol(promotion_piece.upper()))=="N"):
        return chess.KNIGHT
    elif(str(chess.Piece.from_symbol(promotion_piece.upper()))=="B"):
        return chess.BISHOP  

def send_move(move):
    client_socket.send(move.uci().encode())

def receive_moves():
    while True:
        try:
            move_uci = client_socket.recv(1024).decode()
            move = chess.Move.from_uci(move_uci)
            board.push(move)
            update_board()  
        except Exception as e:
            print(e)
            break




def player_move(move):
    if board.piece_at(move.from_square).color == chess.WHITE and (board.piece_at(move.from_square).piece_type == chess.PAWN and chess.square_rank(move.to_square) in [7, 7]):
        promotion_piece = ask_for_promotion_piece()
        move.promotion = promotion_piece  
    if board.piece_at(move.from_square).color == chess.BLACK and (board.piece_at(move.from_square).piece_type == chess.PAWN and chess.square_rank(move.to_square) in [0, 7]):
        promotion_piece = ask_for_promotion_piece()
        move.promotion = promotion_piece  

    if(game_mode=="multi"):
        send_move(move)
    board.push(move)
    update_board()
    if(game_mode=="single"):
        ai_move(level_var.get()) 

def easy_ai_move():
    legal_moves = list(board.legal_moves)
    ai_move = random.choice(legal_moves)
    return ai_move

def ai_move(level):
    update_board()
    if level == "easy":
        move = easy_ai_move()
    elif level == "hard":
        move = find_best_move(board, depth=5)
    board.push(move)
    update_board()

def find_best_move(board, depth):
    legal_moves = list(board.legal_moves)
    best_move = None
    best_eval = -float('inf')

    for move in legal_moves:
        board.push(move)
        eval = minimax(board, depth - 1, -float('inf'), float('inf'), False)
        if eval > best_eval:
            best_eval = eval
            best_move = move
        board.pop()

    return best_move

def minimax(board, depth, alpha, beta, maximizing_player):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)

    legal_moves = list(board.legal_moves)

    if maximizing_player:
        max_eval = -float('inf')
        for move in legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta, False)
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
            eval = minimax(board, depth - 1, alpha, beta, True)
            min_eval = min(min_eval, eval)
            beta = min(beta, eval)
            board.pop()
            if beta <= alpha:
                break
        return min_eval

def evaluate_board(board):
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

status_label = tk.Label(root, text="", font=("Arial", 10))
status_label.pack()


new_game_button = ttk.Button(root, text="New Game", command=lambda: new_game())
new_game_button.pack()

def new_game():
    board.set_fen(chess.STARTING_FEN)
    update_board()
    status_label.config(text="New game started.")

def single_player():
    global game_mode
    game_mode="single"
    enable_buttons()
    level = level_var.get()
    new_game()
    ai_move(level)
    status_label.config(text="Single-player game started. You are playing as White.")

def multi_player():
    global game_mode
    game_mode="multi"
    username_entry.config(state="normal")
    connect_button.config(state="normal")
    disable_buttons()
    status_label.config(text="Multi-player game started.")

level_label = tk.Label(root, text="Choose AI level:")
level_label.pack()

level_var = tk.StringVar()
level_var.set("easy")

easy_radio = tk.Radiobutton(root, text="Easy", variable=level_var, value="easy")
easy_radio.pack()
hard_radio = tk.Radiobutton(root, text="Hard", variable=level_var, value="hard")
hard_radio.pack()

single_player_button = ttk.Button(root, text="Start Single Player", command=single_player)
single_player_button.pack()

multi_player_button = ttk.Button(root, text="Start Multi Player", command=multi_player)
multi_player_button.pack()


def disable_buttons():
    single_player_button.config(state="disabled")
    multi_player_button.config(state="disabled")
    easy_radio.config(state="disabled")
    hard_radio.config(state="disabled")
    new_game_button.config(state="disabled")
    canvas.delete("all")

def enable_buttons():
    if(game_mode=="multi"):
        single_player_button.config(state="normal")
    else:
        multi_player_button.config(state="normal")
        easy_radio.config(state="normal")
        hard_radio.config(state="normal")
        new_game_button.config(state="normal")
    canvas.config(state="normal")

selected_square = None
possible_moves = []

def on_square_click(event):
    square_size=50
    global selected_square, possible_moves
    x, y = event.x, event.y
    col = x // square_size
    row = y // square_size
    square = chess.square(col, 7 - row)

    if selected_square is None:
        piece = board.piece_at(square)
        if piece is not None and piece.color == board.turn:
            selected_square = square
            possible_moves = list(board.legal_moves)
            update_board()
            highlight_square(square)
    else:
        
        move = chess.Move(selected_square, square)
        if(board.piece_at(move.from_square).color == chess.BLACK and board.piece_at(move.from_square).piece_type==chess.PAWN and ("1" in str(move))):
            player_move(move)
        elif(board.piece_at(move.from_square).color == chess.WHITE and board.piece_at(move.from_square).piece_type==chess.PAWN and ("8" in str(move))):
            player_move(move)
        elif move in possible_moves:
            player_move(move)
        selected_square = None

def highlight_square(square):
    square_size=50
    col = chess.square_file(square)
    row = 7 - chess.square_rank(square)
    x1 = col * square_size
    y1 = row * square_size
    x2 = x1 + square_size
    y2 = y1 + square_size
    canvas.create_rectangle(x1, y1, x2, y2, outline="blue", width=3)

canvas.bind("<Button-1>", on_square_click)


def on_closing():
    client_socket.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()

