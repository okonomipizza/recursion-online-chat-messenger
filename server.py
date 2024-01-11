import socket
import threading
import sys

#クライアントクラスはサーバにtcp接続をしてきたクライアントを表す
class Client:
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
    #クライアントとの間に確率されたtcpソケットを介してレスポンスを送信
    def send_response(self, header, body):
        self.connection.sendall(header)
        self.connection.sendall(body)


#チャットルームクラスはホストユーザーと参加できるクライアントとそのトークンをもつ
class Chatroom:
    def __init__(self,roomname, password, hostname):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = '0.0.0.0'
        self.server_port = 9002
        self.roomname = roomname
        self.host = hostname
        self.password = password
        self.clients = {}

    def bind(self):
        is_port_valid = False
        while not is_port_valid:
            try:
                self.socket.bind((self.server_address, self.server_port))
                is_port_valid = True
                print('new chatroom "{}" established on {} {}'.format(self.roomname, self.server_address, self.server_port))
            except socket.error as err:
                #portがあいていなかったら次のportを試す
                self.server_port += 1
                if(self.server_port >= 9100):
                    print('server can not accept more clients')
                    sys.exit(1)

    def run(self):
        while True:
            #受信したデータの取り出し
            data, client_address = self.socket.recvfrom(4096)
            
            if data:
                #受信したデータを解析
                usernamelen = ord(data[:1].decode('utf-8'))
                username, message = data[1:usernamelen + 1].decode('utf-8'), data[usernamelen + 1:].decode('utf-8')

                # アクティブユーザーリストにいなければ追加
                if not username in self.clients:
                    self.clients[username] = client_address

                #メッセージをアクティブユーザーへ配信
                delivery_data = f"{username} --> {message}"

                for client in self.clients.keys():
                    if not client == username:
                        self.socket.sendto(delivery_data.encode('utf-8'), (self.clients[client]))
                print('sent {}'.format(delivery_data))

    def adduser(self, username, address):
        self.clients[username] = address

        
#チャットルームの管理を行う{"ルーム名":Chatroomオブジェクト}
chatrooms = {}

def protocol_header(roomname_size, operation, state, password_size, operation_payload_size):
        return roomname_size.to_bytes(1, "big") + operation.to_bytes(1, "big") + state.to_bytes(1, "big") + password_size.to_bytes(1, "big") + operation_payload_size.to_bytes(4, "big")
    
def protocol_body(roomname, password, operation_payload):
    return roomname.encode('utf-8') + password.encode('utf-8') + operation_payload.encode('utf-8')

#tcpソケットにリクエストを送ったクライアントにレスポンスを送る。
def handle_client(client):
    #request_headerをソケットから取得。
    header = client.connection.recv(8)
    roomname_size = int.from_bytes(header[:1], "big")
    operation = int.from_bytes(header[1:2], "big")
    state = int.from_bytes(header[2:3], "big")
    password_size = int.from_bytes(header[3:4], "big")
    username_payload_size = int.from_bytes(header[4:8], "big")

    #request_bodyをソケットから取得。
    roomname = client.connection.recv(roomname_size).decode('utf-8')
    password = client.connection.recv(password_size).decode('utf-8')
    username = client.connection.recv(username_payload_size).decode('utf-8')

    print(f'operation: {operation}')
    print(f'roomname: {roomname}')
    print(f'password: {password}')
    print(f'username: {username}')

    #データを処理中(state:1)であることをユーザへ知らせる
    state = 1
    message = 'Server is processing...'
    res_header = protocol_header(roomname_size, operation, state, password_size, len(message))
    res_body = protocol_body(roomname, password, message)

    client.send_response(res_header, res_body)
 
    #リクエストに応じた処理を行う
    state = 2 #state:2完了
    if operation == 1:
        #チャットルームの新規作製
        chatroom = Chatroom(roomname, password, username)
        chatroom.bind()
        chatrooms[roomname] = chatroom
        print('new chatroom: {} has created'.format(roomname))

        #クライアントへの返信
        payload = str(chatroom.server_port)

        res_header = protocol_header(roomname_size, operation, state, password_size, len(payload.encode('utf-8')))
        res_body = protocol_body(roomname, password, payload)
        client.send_response(res_header, res_body)
        print('invite {} to chatroom: {}'.format(username, roomname))

        #UDPソケットによるチャット開始
        chatroom.run()


    elif operation == 2:
        # チャットルームへの参加
        chatroom = chatrooms[roomname] #既存のチャットルームマップからチャットルームオブジェクトを取得
        if chatroom.password == password:
            payload = str(chatroom.server_port)
            res_header = protocol_header(roomname_size, operation, state, password_size, len(payload.encode('utf-8')))
            res_body = protocol_body(roomname, password, payload)
            client.send_response(res_header, res_body)
            print('invite {} to chatroom: {}'.format(username, roomname))
    else:
        print('failed something')


#tcpソケットへ送られる接続or新規リクエストに対応する
def receive_connection_requests():
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server_adress = '0.0.0.0'
    tcp_server_port = 9001
    print('server start.')
    tcp_socket.bind((tcp_server_adress, tcp_server_port))
    tcp_socket.listen(1)

    while True:
        try:
            connection, client_address = tcp_socket.accept()
            # client_server, client_port = client_address
            print(f'connection from {client_address}')

            #クライアントごとにスレッドを立ち上げて同時進行で処理を行う
            client = Client(connection, client_address)
            thread_for_client = threading.Thread(target=handle_client, args=(client,))
            thread_for_client.start()
        
        finally:
            pass
            
            

def main():
    receive_connection_requests()

if __name__ == "__main__":
    main()



