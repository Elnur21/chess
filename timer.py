import chess
import threading
import time

class TimerManager:
    def __init__(self):
        self.timer_duration = 180  
        self.timer_thread = None
        self.timer_running = False
        self.timer_pause = False
        
    def set_parameters(self,board, minutes,game_mode,points,combo,username, status_label, canvas):
        self.game_mode=game_mode
        self.points=points
        self.combo=combo
        self.username=username
        self.status_label=status_label
        self.board=board
        self.canvas=canvas
        self.minutes=minutes
        
    def stop_timer(self):
        self.timer_running = False
        if self.timer_thread and self.timer_thread.is_alive():
            try:
                self.timer_thread.run(False)
            except:
                self.minutes.configure(text="Game was stopped")


    def start_timer(self, duration):
        self.timer_thread = threading.Thread(target=self.timer_countdown)
        self.timer_running = True
        self.timer_thread.start()
        if(duration):
            self.timer_duration = duration

    def timer_countdown(self):
        while self.timer_running == True:
            minutes, seconds = divmod(self.timer_duration, 60)
            timer_str = '{:02d}:{:02d}'.format(minutes, seconds)
            self.minutes.configure(text=timer_str)

            if(self.timer_running == False):
                break

            time.sleep(1)
            if (self.timer_pause == False):
                self.timer_duration -= 1
            if self.timer_duration <= 0:
                self.end_game_due_to_timeout()
                break

        if (self.timer_running == False):
            if(self.combo.get()=="3 min"):
                self.timer_duration=3*60
            elif(self.combo.get()=="5 min"):
                self.timer_duration=5*60
            else:
                self.timer_duration=8*60

    def end_game_due_to_timeout(self):
        
        if self.board.turn == chess.WHITE:
            self.winner = "Black"
        else:
            self.winner = "White"
        self.status_label.config(text=f"Congratulation! {self.winner} wins!")

        if  self.game_mode == "multi":
            self.points+=1
            self.update_user_points(self.username, self.points)

        self.timer_running=False
        self.canvas.delete("all")
        self.combo.config(state="normal")

        if(self.combo.get()=="3 min"):
            self.timer_duration=3*60
        elif(self.combo.get()=="5 min"):
            self.timer_duration=5*60
        else:
            self.timer_duration=8*60

