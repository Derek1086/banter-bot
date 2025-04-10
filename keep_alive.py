from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    global server_thread
    server_thread = Thread(target=run)
    server_thread.daemon = True
    server_thread.start()
