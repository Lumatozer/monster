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
            in_string=True
            string_quote="\'"
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
                out.append({"type":"variable", "value":cache})
                cache=""
            out.append({"type":"bracket", "value":"}"})
            continue
        if code[i]=="\n":
            continue
        cache+=code[i]
    if cache!="":
        out.append({"type":"variable", "value":cache})
    return out

def parser(tokens, depth=0):
    out=[]
    i=-1
    while True:
        i+=1
        if i>=len(tokens):
            break
        if tokens[i]["type"]=="operator" and tokens[i]["value"]=="<" and len(tokens)-i>=7:
            j=i
            tagStart=[]
            while True:
                j+=1
                if j>=len(tokens):
                    raise Exception("unexpected EOF while parsing HTML file")
                if tokens[j]["type"]=="operator" and tokens[j]["value"]==">":
                    break
                tagStart.append(tokens[j])
            if len(tagStart)==0 or tagStart[0]["type"]!="variable":
                raise Exception("tag starting expected a token of type variable")
            i=j
            tagEnd=[]
            count=1
            while True:
                j+=1
                if j>=len(tokens):
                    raise Exception("unexpected EOF while parsing HTML file"+str(depth))
                tagEnd.append(tokens[j])
                if len(tagEnd)>=4 and tagEnd[len(tagEnd)-4]["type"]=="operator" and tagEnd[len(tagEnd)-4]["value"]=="<" and tagEnd[len(tagEnd)-3]["type"]=="operator" and tagEnd[len(tagEnd)-3]["value"]=="/" and tagEnd[len(tagEnd)-2]==tagStart[0] and tagEnd[len(tagEnd)-1]["type"]=="operator" and tagEnd[len(tagEnd)-1]["value"]==">":
                    count-=1
                    if count==0:
                        tagEnd=tagEnd[:len(tagEnd)-4]
                        break
                    continue
                if len(tagEnd)>=2 and tagEnd[len(tagEnd)-2]["type"]=="operator" and tagEnd[len(tagEnd)-2]["value"]=="<" and tagEnd[len(tagEnd)-1]==tagStart[0]:
                    count+=1
                    continue
            i=j
            tagName=tagStart[0]["value"]
            tagStart=tagStart[1:]
            attributes={}
            index=-1
            while True:
                index+=1
                if index>=len(tagStart):
                    break
                if len(tagStart)-index>=3 and tagStart[index]["type"]=="variable" and tagStart[index+1]["type"]=="operator" and tagStart[index+1]["value"]=="=":
                    if tagStart[index+2]["type"]!="string":
                        attributes[tagStart[index]["value"]]={"type":"signal", "value":tagStart[index+2]["value"]}
                    else:
                        attributes[tagStart[index]["value"]]={"type":"raw", "value":tagStart[index+2]["value"]}
                    index+=2
                    continue
                attributes[tagStart[index]["value"]]={"type":"raw", "value":"true"}
            out.append({"type":"tag", "value":tagName, "children":parser(tagEnd, depth=depth+1), "attributes":attributes})
            continue
        out.append(tokens[i])
    return out

def init(app):
    MonsterApp=App()
    @app.route('/<path:path>')
    def catch_all(path):
        return MonsterApp.default_Route(path)
    return MonsterApp