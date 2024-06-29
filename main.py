from flask import Flask, request, redirect
from monster import render, init, tokeniser, parser
import sys, json

app = Flask(__name__)
init(app)

@app.get("/")
def home():
    signals=open("public/signals.js").read()
    print(tokeniser(open("components/index.html").read()))
    print(parser(tokeniser(open("components/index.html").read())))
    return render("index", locals())

app.run(host="0.0.0.0", port=int(sys.argv[1]))