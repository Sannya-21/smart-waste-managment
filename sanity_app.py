from flask import Flask
app = Flask(__name__)
@app.route('/')
def hello():
    return "SANITY OK"
if __name__ == '__main__':
    print("Starting sanity app on 5050...")
    app.run(host='127.0.0.1', port=5050)
