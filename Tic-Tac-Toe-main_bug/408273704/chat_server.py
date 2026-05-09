"""
Created on Tue Jul 22 00:47:05 2014

@author: alina, zzhang
"""

import time
import socket
import select
import sys
import string
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
LOCAL_UP3_DIR = PROJECT_DIR / "UP3"
COURSE_UP3_DIR = PROJECT_DIR.parent / "UP3"
UP3_DIR = LOCAL_UP3_DIR if LOCAL_UP3_DIR.exists() else COURSE_UP3_DIR

for import_dir in reversed((BASE_DIR, UP3_DIR)):
    if import_dir.exists() and str(import_dir) not in sys.path:
        sys.path.insert(0, str(import_dir))

import indexer
import json
import pickle as pkl
from chat_utils import *
import chat_group as grp


player_scores = {}


class Server:
    def __init__(self):
        self.new_clients = []  # list of new sockets of which the user id is not known
        self.logged_name2sock = {}  # dictionary mapping username to socket
        self.logged_sock2name = {}  # dict mapping socket to user name
        self.all_sockets = []
        self.group = grp.Group()
        # start server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Listen on all network interfaces so other computers on the same network
        # can connect using this computer's LAN IP address.
        self.server.bind(("0.0.0.0", CHAT_PORT))
        self.server.listen(5)
        self.all_sockets.append(self.server)
        # initialize past chat indices
        self.indices = {}
        # sonnet
        old_cwd = os.getcwd()
        try:
            if UP3_DIR.exists():
                os.chdir(UP3_DIR)
            self.sonnet = indexer.PIndex("AllSonnets.txt")
        finally:
            os.chdir(old_cwd)

    def broadcast_leaderboard(self):
        sorted_scores = sorted(
            player_scores.items(),
            key=lambda item: item[1],
            reverse=True
        )
        leaderboard_text = ", ".join(
            f"{name}:{score}"
            for name, score in sorted_scores
        )
        leaderboard_msg = json.dumps({
            "action": "leaderboard",
            "message": f"/leaderboard {leaderboard_text}"
        })

        for sock in list(self.logged_name2sock.values()):
            mysend(sock, leaderboard_msg)

    def forward_to_chat_group(self, from_sock, msg):
        from_name = self.logged_sock2name[from_sock]
        msg["from"] = from_name
        the_guys = self.group.list_me(from_name)[1:]

        if len(the_guys) == 0:
            mysend(from_sock, json.dumps({
                "action": "system",
                "message": "No connected peer. Connect to a peer before starting a network game."
            }))
            return

        for g in the_guys:
            to_sock = self.logged_name2sock[g]
            mysend(to_sock, json.dumps(msg))

    def new_client(self, sock):
        # add to all sockets and to new clients
        print('new client...')
        sock.setblocking(0)
        self.new_clients.append(sock)
        self.all_sockets.append(sock)

    def login(self, sock):
        # read the msg that should have login code plus username
        try:
            msg = json.loads(myrecv(sock))
            if len(msg) > 0:

                if msg["action"] == "login":
                    name = msg["name"]
                    if self.group.is_member(name) != True:
                        # move socket from new clients list to logged clients
                        self.new_clients.remove(sock)
                        # add into the name to sock mapping
                        self.logged_name2sock[name] = sock
                        self.logged_sock2name[sock] = name
                        # load chat history of that user
                        if name not in self.indices.keys():
                            try:
                                self.indices[name] = pkl.load(
                                    open(name + '.idx', 'rb'))
                            except IOError:  # chat index does not exist, then create one
                                self.indices[name] = indexer.Index(name)
                        print(name + ' logged in')
                        self.group.join(name)
                        mysend(sock, json.dumps(
                            {"action": "login", "status": "ok"}))
                    else:  # a client under this name has already logged in
                        mysend(sock, json.dumps(
                            {"action": "login", "status": "duplicate"}))
                        print(name + ' duplicate login attempt')
                else:
                    print('wrong code received')
            else:  # client died unexpectedly
                self.logout(sock)
        except:
            self.all_sockets.remove(sock)

    def logout(self, sock):
        # remove sock from all lists
        name = self.logged_sock2name[sock]
        pkl.dump(self.indices[name], open(name + '.idx', 'wb'))
        del self.indices[name]
        del self.logged_name2sock[name]
        del self.logged_sock2name[sock]
        self.all_sockets.remove(sock)
        self.group.leave(name)
        sock.close()

# ==============================================================================
# main command switchboard
# ==============================================================================
    def handle_msg(self, from_sock):
        # read msg code
        msg = myrecv(from_sock)
        if len(msg) > 0:
            # ==============================================================================
            # handle connect request this is implemented for you
            # ==============================================================================
            msg = json.loads(msg)
            if msg["action"] == "connect":
                to_name = msg["target"]
                from_name = self.logged_sock2name[from_sock]
                if to_name == from_name:
                    msg = json.dumps({"action": "connect", "status": "self"})
                # connect to the peer
                elif self.group.is_member(to_name):
                    to_sock = self.logged_name2sock[to_name]
                    self.group.connect(from_name, to_name)
                    the_guys = self.group.list_me(from_name)
                    msg = json.dumps(
                        {"action": "connect", "status": "success"})
                    for g in the_guys[1:]:
                        to_sock = self.logged_name2sock[g]
                        mysend(to_sock, json.dumps(
                            {"action": "connect", "status": "request", "from": from_name}))
                else:
                    msg = json.dumps(
                        {"action": "connect", "status": "no-user"})
                mysend(from_sock, msg)
# ==============================================================================
# handle messeage exchange: IMPLEMENT THIS
# ==============================================================================
            elif msg["action"] == "exchange":
                from_name = self.logged_sock2name[from_sock]
                message_text = msg.get("message", "")

                if message_text.startswith("/score"):
                    try:
                        score_delta = int(message_text.split()[1])
                    except (IndexError, ValueError):
                        score_delta = 1

                    player_scores[from_name] = player_scores.get(from_name, 0) + score_delta
                    self.broadcast_leaderboard()
                    return

                """
                Finding the list of people to send to and index message
                """
                # IMPLEMENTATION
                # ---- start your code ---- #
                # 第一步：把消息添加到该用户的聊天记录索引中
                # 根据你 indexer.py 的实现，方法名可能是 add_msg_and_index 或 add_msg
                self.indices[from_name].add_msg_and_index(msg["message"])
                # ---- end of your code --- #

                the_guys = self.group.list_me(from_name)[1:]
                for g in the_guys:
                    to_sock = self.logged_name2sock[g]

                    # IMPLEMENTATION
                    # ---- start your code ---- #
                    # 第二步：将完整的 msg 字典转回 json 字符串，发给其他人
                    mysend(to_sock, json.dumps(msg))
                    # 注意：一定要把原本占位的那句 mysend(to_sock, "...Remember to index...") 删掉！
                    # ---- end of your code --- #
            elif msg["action"] in ["game_start", "game_move", "game_reset"]:
                self.forward_to_chat_group(from_sock, msg)
            elif msg["action"] == "disconnect":
                from_name = self.logged_sock2name[from_sock]
                the_guys = self.group.list_me(from_name)
                self.group.disconnect(from_name)
                the_guys.remove(from_name)
                if len(the_guys) == 1:  # only one left
                    g = the_guys.pop()
                    to_sock = self.logged_name2sock[g]
                    mysend(to_sock, json.dumps(
                        {"action": "disconnect", "msg": "everyone left, you are alone"}))
            elif msg["action"] == "list":

                # IMPLEMENTATION
                # ---- start your code ---- #
                msg = self.group.list_all()

                # ---- end of your code --- #
                mysend(from_sock, json.dumps(
                    {"action": "list", "results": msg}))
# ==============================================================================
#             retrieve a sonnet : IMPLEMENT THIS
# ==============================================================================
            elif msg["action"] == "poem":

                # IMPLEMENTATION
                # ---- start your code ---- #
                poem_idx = int(msg["target"])
                poem = self.sonnet.get_poem(poem_idx)
                print('here:\n', poem)
                if type(poem) == list:
                    poem = '\n'.join(poem)
                # ---- end of your code --- #

                mysend(from_sock, json.dumps(
                    {"action": "poem", "results": poem}))
# ==============================================================================
#                 time
# ==============================================================================
            elif msg["action"] == "time":
                ctime = time.strftime('%d.%m.%y,%H:%M', time.localtime())
                mysend(from_sock, json.dumps(
                    {"action": "time", "results": ctime}))
# ==============================================================================
#                 search: : IMPLEMENT THIS
# ==============================================================================
            elif msg["action"] == "search":

                # IMPLEMENTATION
                # ---- start your code ---- #
                from_name = self.logged_sock2name[from_sock]
                term = msg["target"]
                search_rslt = self.indices[from_name].search(term)

                if type(search_rslt) == list:
                    search_rslt = '\n'.join([str(item) for item in search_rslt])
                print('server side search: ' + search_rslt)

                # ---- end of your code --- #
                mysend(from_sock, json.dumps(
                    {"action": "search", "results": search_rslt}))

# ==============================================================================
#                 the "from" guy really, really has had enough
# ==============================================================================

        else:
            # client died unexpectedly
            self.logout(from_sock)

# ==============================================================================
# main loop, loops *forever*
# ==============================================================================
    def run(self):
        print('starting server...')
        while(1):
            read, write, error = select.select(self.all_sockets, [], [])
            print('checking logged clients..')
            for logc in list(self.logged_name2sock.values()):
                if logc in read:
                    self.handle_msg(logc)
            print('checking new clients..')
            for newc in self.new_clients[:]:
                if newc in read:
                    self.login(newc)
            print('checking for new connections..')
            if self.server in read:
                # new client request
                sock, address = self.server.accept()
                self.new_client(sock)


def main():
    server = Server()
    server.run()


if __name__ == '__main__':
    main()
