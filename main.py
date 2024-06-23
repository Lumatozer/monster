from flask import Flask, request, redirect
from monster import render, init
import sys, json

app = Flask(__name__)
init(app)

@app.get("/")
def home():
    ip_address=request.remote_addr
    ip=render("ip", locals())
    return render("index", locals())

app.run(host="0.0.0.0", port=int(sys.argv[1]))