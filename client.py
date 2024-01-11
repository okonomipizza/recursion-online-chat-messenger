import socket
import sys

tcp_server_adress = '0.0.0.0'
tcp_server_port = 9001

class UDP_Socket:
    def __init__(self, username, server_address, server_port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = server_address
        self.server_port = server_port
        self.username = username
        self.address = ''
        self.port = 9003

    def bind(self):
        is_port_valid = False
        while not is_port_valid:
            try:
                self.socket.bind((self.address, self.port))
                is_port_valid = True
            except socket.error as err:
                #portがあいていなかったら次のportを試す
                self.port += 1
                if(self.port == 9050):
                    sys.exit(1)
        print('connecting to {}{}'.format(self.server_address, self.server_port))
            

    def get_message(self):
        return input('Type in message: ')
    
    def send_message(self):
        usernamelen = len(self.username.encode('utf-8')).to_bytes(1, "big")
        message = self.get_message()
        send_data = usernamelen + self.username.encode('utf-8') + message.encode('utf-8')
        self.socket.sendto(send_data, (self.server_address, self.server_port))

    def run(self):
        while True:
            #入力モードからスタート。入力しなくてもok
            is_modeselect_finish = False
            while not is_modeselect_finish:
                mode = input('will you send any message? (y/n): ')
                if mode == 'y':
                    self.send_message()
                    is_modeselect_finish = True
                elif mode == 'n':
                    is_modeselect_finish = True

            #入力工程が終わったらサーバからの応答をまつ
            while True:
                print('waiting to receive')
                data, server = self.socket.recvfrom(4096)
                if data:
                    print(data.decode('utf-8'))
                    break

def get_username():
    #ユーザー名とメッセージを入力
    username = ""
    is_username_valid = False
    while not is_username_valid:
        username = input('Type in your name: ')
        if len(username.encode('utf-8')) > pow(2, 8):
            print('User name is too long')
        else:
            is_username_valid = True
    return username


def get_operation():
    is_input_valid = False
    while not is_input_valid:
        operation = int(input('Choose command\nCreate new chat room -> 1\nGet in exist chat room -> 2\n: '))
        if operation == 1 or operation == 2:
            is_input_valid = True
            return operation


def get_chatroom_name(operation):
    question = ''
    if operation == 1: #新規作製のとき
        question = 'Type in new chatroom name: '
    elif operation == 2: #既存のチャットルームを指定するとき
        question = 'Type in chatroom name that you want to join: '

    chatroom_name = input(question)
    return chatroom_name


def get_password(operation):
    if operation == 1:
        return input('Set a password: ')
    else:
        return input('Type in password: ')


def protocol_header(roomname_size, operation, state, password_size, operation_payload_size):
    return roomname_size.to_bytes(1, "big") + operation.to_bytes(1, "big") + state.to_bytes(1, "big") + password_size.to_bytes(1, "big") + operation_payload_size.to_bytes(4, "big")


def protocol_body(roomname, password, operation_payload):
    return roomname.encode('utf-8') + password.encode('utf-8') + operation_payload.encode('utf-8')


def main():
    username = get_username()
    udp_address = '0.0.0.0'
    udp_port = 9004

    #TCPソケットに接続
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print('connecting to {} {}'.format(tcp_server_adress, tcp_server_port))
    try:
        tcp_socket.connect((tcp_server_adress, tcp_server_port))
        print('successfully conected to {} {} by tcp socket'.format(tcp_server_adress, tcp_server_port))
    except socket.error as err:
        print(err)
        sys.exit(1)

    try:
        #リクエストを作製
        operation = get_operation()
        chatroomname = get_chatroom_name(operation)
        password = get_password(operation)
        state = 0

        header = protocol_header(len(chatroomname.encode('utf-8')), operation, state, len(password.encode('utf-8')), len(username.encode('utf-8')))
        body = protocol_body(chatroomname, password, username)

        #リクエストを送信
        tcp_socket.send(header)
        tcp_socket.send(body)

        #サーバからの返信(state=1)を受信する。これはサーバが情報を受け取って処理中であることを表す。
        res_header = tcp_socket.recv(8)
        chatroomname_size = int.from_bytes(res_header[:1], "big")
        operation = int.from_bytes(res_header[1:2], "big")
        status = int.from_bytes(res_header[2:3], "big")
        password_size = int.from_bytes(res_header[3:4], "big")
        payload_length = int.from_bytes(res_header[4:8], "big")

        #次に送られたbodyを取得
        chatroomname = tcp_socket.recv(chatroomname_size).decode('utf-8')
        password = tcp_socket.recv(password_size).decode('utf-8')
        payload = tcp_socket.recv(payload_length).decode('utf-8')
        print('status {}: {}'.format(status, payload))

        #サーバからの完了報告を受信する
        res_header = tcp_socket.recv(8)
        chatroomname_size = int.from_bytes(res_header[:1], "big")
        operation = int.from_bytes(res_header[1:2], "big")
        status = int.from_bytes(res_header[2:3], "big")
        password_size = int.from_bytes(res_header[3:4], "big")
        payload_length = int.from_bytes(res_header[4:8], "big")

        print(f'json_size: {payload_length}')

        chatroomname = tcp_socket.recv(chatroomname_size).decode('utf-8')
        password = tcp_socket.recv(password_size).decode('utf-8')
        udp_port = int(tcp_socket.recv(payload_length).decode('utf-8'))

        print(f"Received JSON data: {udp_port}")



    finally:
        tcp_socket.close()

    #サーバから送られたトークン(udpソケットのアドレス)に接続

    
    udp_socket = UDP_Socket(username, udp_address, udp_port)
    udp_socket.bind()
    udp_socket.run()





if __name__ == "__main__":
    main()





    
