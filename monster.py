from os import PathLike
import uuid, json, base64, flask
from flask import send_from_directory, request, Flask
from urllib.parse import quote
import traceback

FlaskClass=Flask

def escapeString(a):
    return a.replace("\\", "\\\\").replace("\"", "\\\"").replace("'", "\\'").replace("\n", "\\n").replace("`", "\\`").replace("</script>", "</`+`script>")

def djb2_hash(s):
    hash = 5381
    for char in s:
        hash = ((hash << 5) + hash) + ord(char)
    return hash & 0xFFFFFFFF

MonsterSave="""
<script>
    var MONSTERSIGNALS="{monster_base64}"
    eval(atob(MONSTERSIGNALS))
    window.localStorage.setItem("MONSTERSIGNALS", MONSTERSIGNALS)
    document.cookie="MONSTERSIGNALS=true;expires=Thu, 01 Jan 2049 00:00:00 UTC"
</script>""".strip(" \n").replace("{monster_base64}", base64.b64encode(open("public/signals.js", "rb").read()).decode())

MonsterDefault="""
<script>
    function djb2Hash(t){t=String(t);let e=5381;for(let n=0;n<t.length;n++){e=(e<<5)+e+t.charCodeAt(n)}return e>>>0}
    if (String(djb2Hash(window.localStorage.getItem("MONSTERSIGNALS")))!="{version_hash}") {
        document.cookie="MONSTERSIGNALS=false;expires=Thu, 01 Jan 2049 00:00:00 UTC"
        window.location=String(window.location)
    } else {
        eval(atob(window.localStorage.getItem("MONSTERSIGNALS")))
    }
</script>
""".replace("{version_hash}", str(djb2_hash(base64.b64encode(open("public/signals.js", "rb").read()).decode())))

class Render():
    def __init__(self, render="") -> None:
        self.render=render

class Flask(Flask):
    def __init__(self, import_name: str, static_url_path: str | None = None, static_folder: str | PathLike | None = "static", static_host: str | None = None, host_matching: bool = False, subdomain_matching: bool = False, template_folder: str | None = "templates", instance_path: str | None = None, instance_relative_config: bool = False, root_path: str | None = None):
        super().__init__(import_name, static_url_path, static_folder, static_host, host_matching, subdomain_matching, template_folder, instance_path, instance_relative_config, root_path)
        @self.route('/<path:path>')
        def catch_all(path):
            return send_from_directory("public", path)
    def make_response(self, object):
        if isinstance(object, Render):
            if "MONSTERSIGNALS" in request.cookies:
                if request.cookies["MONSTERSIGNALS"]!="true":
                    return FlaskClass.response_class(MonsterSave+object.render)
                else:
                    return FlaskClass.response_class(MonsterDefault+object.render)
            else:
                return FlaskClass.response_class(MonsterSave+object.render)
        return super().make_response(object)

def set_headers(response, path):
    if path.endswith('.js'):
        response.headers['Content-Type'] = 'application/javascript'
    elif path.endswith('.css'):
        response.headers['Content-Type'] = 'text/css'
    elif path.endswith('.png'):
        response.headers['Content-Type'] = 'image/png'
    elif path.endswith('.jpg') or path.endswith('.jpeg'):
        response.headers['Content-Type'] = 'image/jpeg'
    elif path.endswith('.gif'):
        response.headers['Content-Type'] = 'image/gif'
    elif path.endswith('.woff2'):
        response.headers['Content-Type'] = 'font/woff2'
    response.headers["Cache-Control"]="no-cache, no-store, must-revalidate"
    response.headers["Pragma"]="no-cache"
    response.headers["Expires"]="0"
    return response

def render(path, variables={}):
    tokenise=path.endswith(".html")
    try:
        component=open(path).read()
    except:
        component=open("components/"+path+".html").read()
        tokenise=True
    component=ssr(component, variables)
    if tokenise:
        pass
    print(tokeniser(component))
    return Render(component)

def ssr(code, variables={}):
    pysegments={}
    toreplace=[]
    buffer=""
    i=-1
    code_len=len(code)
    while True:
        i+=1
        if i>=code_len:
            break
        buffer+=code[i]
        if buffer.endswith("<py>"):
            buffer=""
            while True:
                i+=1
                if i>=code_len:
                    break
                buffer+=code[i]
                if buffer.endswith("</py>"):
                    break
            uid=uuid.uuid4().__str__()
            pysegments[uid]=buffer[:len(buffer)-5]
            toreplace.append(["<py>"+buffer, uid])
            buffer=""
    for x in toreplace:
        code=str(code).replace(x[0], x[1], 1)
    for x in pysegments:
        try:
            result=eval(pysegments[x])
            if type(result)!=str:
                result=json.dumps(result)
            code=str(code.replace(x, result))
        except:
            exec("result=None", variables)
            base="\n".join([" "+x for x in pysegments[x].split("\n")])
            if base!="":
                to_evaluate="def _():\n"+base+"\nresult=_()"
            exec(to_evaluate, variables)
            if type(variables["result"])!=str:
                variables["result"]=json.dumps(variables["result"])
            code=str(code.replace(x, variables["result"]))
    return code

def innertokeniser(code):
    out=[]
    buffer=""
    instring=False
    ascii="abcdefghijklmnopqrstuvwxyz"
    ascii+=ascii.upper()+"1234567890_"
    for x in code:
        if not instring and x == "\"":
            if buffer!="":
                out.append({"type":"variable", "content":buffer})
                buffer=""
            instring=True
            continue
        if instring and x=="\"" and not buffer.endswith("\\"):
            instring=False
            out.append({"type":"string", "content":buffer})
            buffer=""
            continue
        if not instring and x==" ":
            if buffer!="":
                out.append({"type":"variable", "content":buffer})
                buffer=""
            continue
        if not instring and x in "{}[]()-+<>=*^%!@~/":
            if buffer!="":
                out.append({"type":"variable", "content":buffer})
                buffer=""
            out.append({"type":"operator", "content":x})
            continue
        buffer+=x
    if buffer!="":
        out.append({"type":"variable", "content":buffer})
    return out

def tokeniser(code):
    out=[]
    i=-1
    code_len=len(code)
    rawtext=""
    while True:
        i+=1
        if i>=code_len:
            break
        elif code[i]=="<":
            if rawtext!="":
                out.append({"type":"raw", "content":rawtext})
                rawtext=""
            buffer=""
            while True:
                i+=1
                if i>=code_len:
                    raise EOFError
                if code[i]==">":
                    break
                buffer+=code[i]
            name=buffer.split(" ", 1)[0]
            buffer=buffer[len(name):]
            args={}
            tokens=innertokeniser(buffer)
            j=-1
            tokens_len=len(tokens)
            while True:
                j+=1
                if j>=tokens_len:
                    break
                if tokens_len-j>=3 and tokens[j]["type"]=="variable" and tokens[j+1]["type"]=="operator" and tokens[j+1]["content"]=="=" and tokens[j+2]["type"]=="string":
                    args[tokens[j]["content"]]=tokens[j+2]["content"]
                    j+=2
                    continue
                if tokens[j]["type"] in ["operator", "string"]:
                    continue
                if tokens[j]["type"]=="variable":
                    args[tokens[j]["content"]]=True
            buffer=""
            count=1
            while True:
                i+=1
                if i>=code_len:
                    raise EOFError
                buffer+=code[i]
                if buffer.endswith("</"+name+">"):
                    count-=1
                if buffer.endswith("<"+name):
                    count+=1
                if count==0:
                    break
            buffer=buffer[:len(buffer)-len("</"+name+">")]
            out.append({"type":"tag", "tag":name, "args":args, "children":tokeniser(buffer)})
            buffer=""
            continue
        rawtext+=code[i]
    if rawtext!="":
        out.append({"type":"raw", "content":rawtext})
    return out