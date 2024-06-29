import uuid, json
from flask import send_from_directory

class App:
    def __init__(self) -> None:
        def default_Route(path):
            response=send_from_directory("public", path)
            return set_headers(response, path)
        self.default_Route=default_Route
    def on_404(self, path):
        return "Error: 404 Not Found /"+path

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

def render(path, variables=None):
    try:
        component=open(path).read()
    except:
        component=open("components/"+path+".html").read()
    if variables==None:
        variables=locals()|globals()
    replace_maps={}
    for variable in variables:
        if "{"+variable+"}" in component:
            uid=uuid.uuid4().__str__()
            replace_maps[uid]=variable
            component=component.replace("{"+variable+"}", uid)
    for x in replace_maps:
        out=variables[replace_maps[x]]
        if type(out) in [int, float, dict]:
            out=json.dumps(out)
        if type(out)==list:
            out="\n".join([str(x) for x in out])
        component=component.replace(x, out)
    return component

def Tag():
    return {"name":"", "attributes":{}, "signals":[], "children":[]}

def Attribute():
    return {"id":"", "value":""}

def tokeniser(code):
    out=[]
    i=-1
    cache=""
    in_string=False
    string_quote=""
    while True:
        i+=1
        if i>=len(code):
            break
        if in_string:
            if code[i]==string_quote:
                out.append({"type":"string", "value":cache})
                cache=""
                in_string=False
                continue
            cache+=code[i]
            continue
        if code[i]=="\"":
            in_string=True
            string_quote="\""
            continue
        if code[i]=="'":
            out.append({"type":"quote", "value":"'"})
            continue
        if code[i]=="<":
            if cache!="":
                out.append({"type":"variable", "value":cache})
                cache=""
            out.append({"type":"operator", "value":"<"})
            continue
        if code[i]==">":
            if cache!="":
                out.append({"type":"variable", "value":cache})
                cache=""
            out.append({"type":"operator", "value":">"})
            continue
        if code[i]=="=":
            if cache!="":
                out.append({"type":"variable", "value":cache})
                cache=""
            out.append({"type":"operator", "value":"="})
            continue
        if code[i]=="/":
            if cache!="":
                out.append({"type":"variable", "value":cache})
                cache=""
            out.append({"type":"operator", "value":"/"})
            continue
        if code[i]==" ":
            if cache!="":
                out.append({"type":"variable", "value":cache})
                cache=""
            continue
        if code[i]=="{":
            if cache!="":
                out.append({"type":"variable", "value":cache})
                cache=""
            out.append({"type":"bracket", "value":"{"})
            continue
        if code[i]=="}":
            if cache!="":
                out.append({"type":"variable", "value":"}"})
                cache=""
            out.append({"type":"bracket", "value":"}"})
            continue
        if code[i]=="\n":
            continue
        cache+=code[i]
    if cache!="":
        out.append({"type":"variable", "value":cache})
    return out

def parser(component):
    out=[]
    reading_tag=0
    tag_name=""
    for x in component:
        if x=="<" and reading_tag==0:
            reading_tag=1

def init(app):
    MonsterApp=App()
    @app.route('/<path:path>')
    def catch_all(path):
        return MonsterApp.default_Route(path)
    return MonsterApp