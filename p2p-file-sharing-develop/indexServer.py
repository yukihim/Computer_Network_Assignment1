from server.server import Server



if __name__ == '__main__':
    server = Server()

    server.start()
    while True:
        if input() == "end":
            server.stop()
            break
        