import json
import socket
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
UP3_DIR = PROJECT_DIR.parent / "UP3"

for import_dir in reversed((BASE_DIR, PROJECT_DIR, UP3_DIR)):
    if import_dir.exists() and str(import_dir) not in sys.path:
        sys.path.insert(0, str(import_dir))

from ai_image_utils import generate_ai_image
from chat_utils import CHAT_PORT, SERVER, myrecv, mysend
from nlp_utils import extract_keywords, summarize_chat
from sentiment_utils import format_sentiment_label
from tic_tac_toe import TicTacToe

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


class ChatGameClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat + Tic-Tac-Toe + Sentiment")
        self.root.geometry("1080x720")

        self.sock = None
        self.username = ""
        self.running = False
        self.game = None
        self.chat_lines = []
        self.generated_image = None
        self.peer_name = ""

        self.build_login_ui()

    def build_login_ui(self):
        self.login_frame = tk.Frame(self.root, padx=16, pady=16)
        self.login_frame.pack(fill="both", expand=True)

        tk.Label(self.login_frame, text="Username").grid(row=0, column=0, sticky="w")
        self.name_entry = tk.Entry(self.login_frame, width=28)
        self.name_entry.grid(row=0, column=1, padx=8, pady=6)

        tk.Label(self.login_frame, text="Server IP").grid(row=1, column=0, sticky="w")
        self.host_entry = tk.Entry(self.login_frame, width=28)
        self.host_entry.insert(0, SERVER[0])
        self.host_entry.grid(row=1, column=1, padx=8, pady=6)

        tk.Button(self.login_frame, text="Login", command=self.login).grid(
            row=2, column=0, columnspan=2, pady=12
        )

        self.name_entry.focus_set()
        self.root.bind("<Return>", lambda event: self.login())

    def build_chat_ui(self):
        self.root.bind("<Return>", lambda event: self.send_chat_message())
        self.login_frame.destroy()

        main = tk.Frame(self.root, padx=10, pady=10)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=0)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(1, weight=1)

        top_bar = tk.Frame(main)
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        top_bar.columnconfigure(1, weight=1)

        tk.Label(top_bar, text=f"Logged in as: {self.username}").grid(row=0, column=0, sticky="w")
        self.status_label = tk.Label(top_bar, text="Not connected to a peer")
        self.status_label.grid(row=0, column=1, sticky="w", padx=16)
        tk.Label(top_bar, text="Bonus Topics 1, 2, 3 enabled").grid(row=0, column=2, sticky="e")

        game_panel = tk.Frame(main, bg="#222222", padx=8, pady=8)
        game_panel.grid(row=1, column=0, rowspan=2, sticky="n", padx=(0, 12))
        self.game = TicTacToe(
            game_panel,
            send_network_msg_func=self.send_network_msg,
            send_game_event_func=self.send_game_event
        )

        right_panel = tk.Frame(main)
        right_panel.grid(row=1, column=1, rowspan=2, sticky="nsew")
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=1)

        side = tk.Frame(right_panel)
        side.grid(row=0, column=0, sticky="ew")
        side.columnconfigure(1, weight=1)

        tk.Label(side, text="Global Leaderboard", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.leaderboard_listbox = tk.Listbox(side, width=28, height=8)
        self.leaderboard_listbox.grid(row=1, column=0, rowspan=4, sticky="nsw", pady=(4, 12), padx=(0, 12))
        self.leaderboard_listbox.insert(tk.END, "No scores yet")

        tk.Label(side, text="Peer username").grid(row=1, column=1, sticky="w")
        self.peer_entry = tk.Entry(side, width=28)
        self.peer_entry.grid(row=2, column=1, sticky="ew", pady=(4, 6))
        tk.Button(side, text="Connect Peer", command=self.connect_peer).grid(row=3, column=1, sticky="ew")
        tk.Button(side, text="Who Is Online", command=self.request_user_list).grid(row=4, column=1, sticky="ew", pady=(6, 0))
        tk.Button(side, text="Disconnect Peer", command=self.disconnect_peer).grid(row=5, column=1, sticky="ew", pady=(6, 0))
        tk.Button(side, text="Start Network Game", command=self.start_network_game).grid(row=6, column=1, sticky="ew", pady=(12, 0))
        tk.Button(side, text="Summarize Chat", command=self.show_chat_summary).grid(row=7, column=1, sticky="ew", pady=(12, 0))
        tk.Button(side, text="Extract Keywords", command=self.show_chat_keywords).grid(row=8, column=1, sticky="ew", pady=(6, 0))
        tk.Label(side, text="AI image prompt").grid(row=9, column=1, sticky="w", pady=(12, 0))
        self.image_prompt_entry = tk.Entry(side, width=28)
        self.image_prompt_entry.grid(row=10, column=1, sticky="ew", pady=(4, 6))
        tk.Button(side, text="Generate AI Image", command=self.generate_image_from_prompt).grid(row=11, column=1, sticky="ew")
        self.image_status_label = tk.Label(side, text="No image generated yet.", anchor="w", justify="left")
        self.image_status_label.grid(row=12, column=1, sticky="ew", pady=(6, 0))

        self.chat_display = scrolledtext.ScrolledText(right_panel, state="disabled", wrap="word", height=18)
        self.chat_display.grid(row=1, column=0, sticky="nsew", pady=(8, 8))

        image_panel = tk.Frame(right_panel)
        image_panel.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        image_panel.columnconfigure(1, weight=1)
        tk.Label(image_panel, text="AI Image Preview").grid(row=0, column=0, sticky="nw", padx=(0, 8))
        self.image_preview_label = tk.Label(
            image_panel,
            text="Generated image will appear here.",
            width=34,
            height=8,
            relief="groove",
            anchor="center",
            justify="center"
        )
        self.image_preview_label.grid(row=0, column=1, sticky="ew")

        bottom = tk.Frame(right_panel)
        bottom.grid(row=3, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)

        self.message_entry = tk.Entry(bottom)
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        tk.Button(bottom, text="Send", command=self.send_chat_message).grid(row=0, column=1)

        self.message_entry.focus_set()
        self.add_chat_line("System: login successful. Sentiment labels appear after chat messages.")

    def login(self):
        username = self.name_entry.get().strip()
        host = self.host_entry.get().strip()

        if not username:
            messagebox.showwarning("Login", "Please enter a username.")
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, CHAT_PORT))
            mysend(self.sock, json.dumps({"action": "login", "name": username}))
            response = json.loads(myrecv(self.sock))
        except Exception as err:
            messagebox.showerror("Login failed", str(err))
            return

        if response.get("status") != "ok":
            messagebox.showerror("Login failed", "Duplicate username or server rejected login.")
            self.sock.close()
            self.sock = None
            return

        self.username = username
        self.running = True
        self.build_chat_ui()

        thread = threading.Thread(target=self.receive_loop, daemon=True)
        thread.start()

    def receive_loop(self):
        while self.running:
            try:
                raw_msg = myrecv(self.sock)
                if not raw_msg:
                    break
                msg = json.loads(raw_msg)
            except Exception:
                break

            self.root.after(0, self.handle_server_message, msg)

        self.root.after(0, self.add_chat_line, "System: disconnected from server.")

    def handle_server_message(self, msg):
        action = msg.get("action")

        if action == "leaderboard":
            payload = msg.get("message", "")
            if payload.startswith("/leaderboard"):
                payload = payload[len("/leaderboard"):].strip()
            self.update_leaderboard(payload)
            return

        if action == "exchange":
            sender = msg.get("from", "")
            message = msg.get("message", "")
            self.add_chat_line(self.format_chat_line(sender, message))
            return

        if action == "connect":
            status = msg.get("status")
            if status == "success":
                if not self.peer_name:
                    self.peer_name = self.peer_entry.get().strip()
                self.status_label.config(text="Connected to peer")
                self.add_chat_line("System: peer connected.")
            elif status == "request":
                peer = msg.get("from", "unknown")
                self.peer_name = peer
                self.status_label.config(text=f"Connected to {peer}")
                self.add_chat_line(f"System: {peer} connected with you.")
            elif status == "self":
                self.add_chat_line("System: you cannot connect to yourself.")
            elif status == "no-user":
                self.add_chat_line("System: user is not online.")
            return

        if action == "disconnect":
            self.status_label.config(text="Not connected to a peer")
            self.add_chat_line("System: " + msg.get("msg", "peer disconnected."))
            return

        if action == "list":
            self.add_chat_line("Online users:\n" + msg.get("results", ""))
            return

        if action == "system":
            self.add_chat_line("System: " + msg.get("message", ""))
            return

        if action == "game_start":
            peer = msg.get("from", "Peer")
            self.peer_name = peer
            self.game.start_network_game("O", x_name=peer, o_name=self.username)
            self.status_label.config(text=f"Network game with {peer}")
            self.add_chat_line(f"System: Network Tic-Tac-Toe started by {peer}. You are O.")
            return

        if action == "game_move":
            self.game.receive_network_move(
                int(msg.get("row")),
                int(msg.get("col")),
                msg.get("player")
            )
            return

        if action == "game_reset":
            self.game.receive_network_reset()
            self.add_chat_line("System: Network game board reset.")
            return

        if action in ("time", "search", "poem"):
            self.add_chat_line(str(msg.get("results", "")))

    def format_chat_line(self, sender, message):
        return f"{sender}{message} {format_sentiment_label(message)}"

    def add_chat_line(self, text):
        self.chat_lines.append(text)
        self.chat_display.config(state="normal")
        self.chat_display.insert(tk.END, text + "\n")
        self.chat_display.config(state="disabled")
        self.chat_display.see(tk.END)

    def show_chat_summary(self):
        summary = summarize_chat(self.chat_lines)
        self.add_chat_line("Chat Summary:\n" + summary)

    def show_chat_keywords(self):
        keywords = extract_keywords(self.chat_lines)
        if keywords:
            self.add_chat_line("Chat Keywords: " + ", ".join(keywords))
        else:
            self.add_chat_line("Chat Keywords: no keywords yet.")

    def generate_image_from_prompt(self):
        prompt = self.image_prompt_entry.get().strip()
        if not prompt:
            messagebox.showwarning("AI Image", "Please enter an image prompt.")
            return

        self.image_status_label.config(text="Generating image...")
        self.add_chat_line("AI Image Prompt: " + prompt)

        thread = threading.Thread(
            target=self._generate_image_worker,
            args=(prompt,),
            daemon=True
        )
        thread.start()

    def _generate_image_worker(self, prompt):
        try:
            image_path = generate_ai_image(prompt, PROJECT_DIR / "generated_images")
        except Exception as err:
            self.root.after(0, self._show_image_error, str(err))
            return

        self.root.after(0, self._show_generated_image, image_path)

    def _show_image_error(self, error_message):
        self.image_status_label.config(text="Image generation failed.")
        self.add_chat_line("AI Image Error: " + error_message)

    def _show_generated_image(self, image_path):
        self.image_status_label.config(text=f"Saved: {image_path.name}")
        self.add_chat_line(f"AI Image Generated: {image_path}")

        if Image is not None and ImageTk is not None:
            image = Image.open(image_path)
            image.thumbnail((220, 220))
            self.generated_image = ImageTk.PhotoImage(image)
            self.image_preview_label.config(image=self.generated_image, text="")
            return

        try:
            self.generated_image = tk.PhotoImage(file=str(image_path))
            self.image_preview_label.config(image=self.generated_image, text="")
        except tk.TclError:
            self.image_preview_label.config(
                image="",
                text="Image saved, but preview needs Pillow.\nRun: pip install pillow"
            )

    def update_leaderboard(self, payload):
        self.leaderboard_listbox.delete(0, tk.END)

        if not payload.strip():
            self.leaderboard_listbox.insert(tk.END, "No scores yet")
            return

        for rank, item in enumerate(payload.split(","), start=1):
            item = item.strip()
            if ":" not in item:
                continue
            name, score = item.split(":", 1)
            self.leaderboard_listbox.insert(tk.END, f"{rank}. {name.strip()} - {score.strip()} pts")

    def connect_peer(self):
        peer = self.peer_entry.get().strip()
        if not peer:
            messagebox.showwarning("Connect", "Please enter a peer username.")
            return
        self.peer_name = peer
        mysend(self.sock, json.dumps({"action": "connect", "target": peer}))

    def request_user_list(self):
        mysend(self.sock, json.dumps({"action": "list"}))

    def disconnect_peer(self):
        mysend(self.sock, json.dumps({"action": "disconnect"}))
        self.peer_name = ""
        self.status_label.config(text="Not connected to a peer")

    def start_network_game(self):
        peer = self.peer_name or self.peer_entry.get().strip()
        if not peer:
            messagebox.showwarning("Network Game", "Connect to a peer before starting a network game.")
            return

        self.peer_name = peer
        self.game.start_network_game("X", x_name=self.username, o_name=peer)
        self.status_label.config(text=f"Network game with {peer}")
        self.add_chat_line(f"System: Network Tic-Tac-Toe started. You are X.")
        mysend(self.sock, json.dumps({
            "action": "game_start",
            "x_name": self.username,
            "o_name": peer
        }))

    def send_chat_message(self):
        text = self.message_entry.get().strip()
        if not text:
            return

        self.message_entry.delete(0, tk.END)
        self.add_chat_line(self.format_chat_line(f"[{self.username}]", text))
        mysend(self.sock, json.dumps({
            "action": "exchange",
            "from": f"[{self.username}]",
            "message": text
        }))

    def send_network_msg(self, text):
        if self.sock is None:
            return

        mysend(self.sock, json.dumps({
            "action": "exchange",
            "from": f"[{self.username}]",
            "message": text
        }))

    def send_game_event(self, event):
        if self.sock is None:
            return

        if event.get("type") == "move":
            mysend(self.sock, json.dumps({
                "action": "game_move",
                "row": event["row"],
                "col": event["col"],
                "player": event["player"]
            }))
        elif event.get("type") == "reset":
            mysend(self.sock, json.dumps({"action": "game_reset"}))

    def close(self):
        self.running = False
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = ChatGameClient(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()


if __name__ == "__main__":
    main()
