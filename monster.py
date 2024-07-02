from os import PathLike
import uuid, json, base64, flask
from flask import send_from_directory, request, Flask

FlaskClass=Flask

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
        console.log(window.location.toString())
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
    try:
        component=open(path).read()
    except:
        component=open("components/"+path+".html").read()
    tokens=tokeniser(component)
    component=renderTokens(parser(tokens=tokens), variables={"env":variables, "variables":{}})
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
        if isinstance(out, Render):
            out=Render.render
        component=component.replace(x, out)
    return Render(component)

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
        if len(out)>=3 and out[len(out)-3]["type"]=="operator" and out[len(out)-3]["value"]=="<" and out[len(out)-2]["type"]=="variable" and out[len(out)-2]["value"] in ["script", "style"] and out[len(out)-1]["type"]=="operator" and out[len(out)-1]["value"]==">":
            tag=out[len(out)-2]["value"]
            out=out[:len(out)-3]
            inTag=""
            j=i
            while True:
                j+=1
                if j>=len(code):
                    raise Exception("unexpected EOF while tokenising html file")
                inTag+=code[j]
                if "</"+tag+">" in inTag and inTag.count("</"+tag+">")==inTag.count("<"+tag+">")+1:
                    inTag=inTag[:len(inTag)-len("</"+tag+">")]
                    break
            i=j
            out.append({"type":tag, "value":inTag, "attributes":{}, "children":[]})
            continue
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

def parser(tokens):
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
                    raise Exception("unexpected EOF while parsing HTML file")
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
                        attributes[tagStart[index]["value"]]={"type":"variable", "value":tagStart[index+2]["value"]}
                    index+=2
                    continue
                attributes[tagStart[index]["value"]]={"type":tagStart[index]["type"], "value":"true"}
            out.append({"type":"tag", "value":tagName, "children":parser(tagEnd), "attributes":attributes})
            continue
        out.append(tokens[i])
    return out

def renderTokens(tokens, variables={"env":{}, "variables":{}}):
    final=""
    i=-1
    while True:
        i+=1
        if i>=len(tokens):
            break
        if len(tokens)-i>=3 and tokens[i]["type"]=="bracket" and tokens[i]["value"]=="{" and tokens[i+1]["type"]=="variable" and tokens[i+2]["type"]=="bracket" and tokens[i+2]["value"]=="}":
            if tokens[i+1]["value"] not in variables["env"] and tokens[i+1]["value"] not in variables["variables"]:
                final+="""
                <script>
                    (()=>{
                        var signal=GetSignal("{id}")
                        var element=document.createElement("span")
                        var value=signal.Value()
                        if (typeof value!="string") {
                            value=JSON.stringify(value)
                        }
                        element.innerText=value
                        document.currentScript.insertAdjacentElement("afterend", element)
                        OnChange("{id}", ()=>{
                            var newElement=document.createElement("span")
                            var value=signal.Value()
                            if (typeof value!="string") {
                                value=JSON.stringify(value)
                            }
                            newElement.innerText=value
                            element.replaceWith(newElement)
                            element=newElement
                        })
                    })()
                </script>
                """.replace("{id}", tokens[i+1]["value"])
            else:
                final+="{"+tokens[i+1]["value"]+"}"+"\n\n"
            i+=2
            continue
        if tokens[i]["type"]=="tag" and tokens[i]["value"] not in ["if", "for"]:
            tag=tokens[i]
            final+="\n<"+tokens[i]["value"]
            script=""
            if len(tag["attributes"])!=0:
                for attribute in tag["attributes"]:
                    if tag["attributes"][attribute]["type"] in ["variable", "signal"]:
                        attributeValue="\""
                        signals=[]
                        cache=""
                        inSignal=False
                        for x in tag["attributes"][attribute]["value"]:
                            if x=="{":
                                if not inSignal:
                                    inSignal=True
                                    continue
                            if x=="}":
                                if inSignal:
                                    inSignal=False
                                    attributeValue+="\"+"+cache+".Value()+\""
                                    signals.append(cache)
                                    cache=""
                                    continue
                            if inSignal:
                                cache+=x
                            else:
                                attributeValue+=x
                        attributeValue+="\""
                        if len(signals)==0:
                            final+=" "+attribute+"="+attributeValue
                            continue
                        script+=f"""
                        parentElement.setAttribute(\"{attribute}\", {attributeValue})
                        var signals={json.dumps(signals)}
                        for (var signal in signals) {{
                            signal=signals[signal]
                            OnChange(signal, ()=>{{
                                parentElement.setAttribute(\"{attribute}\", {attributeValue})
                            }})
                        }}
                        """
            final+=">"+"\n"+renderTokens(tag["children"], variables=variables)+"\n"
            final+="</"+tag["value"]+">"
            if script!="":
                script="var parentElement=document.currentScript.previousElementSibling\n"+script
                final+="\n<script>"+"(()=>{\n"+script+"\n"+"})()"+"</script>"
            continue
        if tokens[i]["type"]=="tag" and tokens[i]["value"]=="if":
            base64Children=base64.b64encode(renderTokens(tokens[i]["children"], variables).encode()).decode()
            script="\n<div></div>\n"+"""<script>\n(()=>{
                var parentElement=document.currentScript.previousElementSibling
                var base64="{base64}"
                var element=document.createElement("div")
                var onDom={condition}
                if ({condition}) {
                    element.innerHTML=atob(base64)
                    parentElement.appendChild(element)
                }
            """.replace("{base64}", base64Children)
            condition=""
            random_uuid=uuid.uuid4().__str__()
            ifscript="""
                    OnChange(\"{attribute}\", ()=>{
                                if ({random_uuid}) {
                                    if (onDom) {
                                        return
                                    }
                                    onDom=true
                                    element=document.createElement("div")
                                    element.innerHTML=atob(base64)
                                    parentElement.replaceWith(element)
                                    parentElement=element
                                    function executeScripts(element) {
                                        element.querySelectorAll("script").forEach(script => {
                                            const newScript = document.createElement("script")
                                            if (script.src) {
                                                newScript.src = script.src
                                            } else {
                                                newScript.textContent = script.textContent
                                            }
                                            script.parentNode.replaceChild(newScript, script)
                                        })
                                    }
                                    executeScripts(parentElement)
                                } else {
                                    try {
                                        parentElement.removeChild(element)
                                        onDom=false
                                    } catch {}
                                }
                    })
                    """
            for attribute in tokens[i]["attributes"]:
                if tokens[i]["attributes"][attribute]["type"]!="string":
                    if attribute.startswith("dep:"):
                        for attribute in attribute[4:].split(":"):
                            script+=ifscript.replace("{random_uuid}", random_uuid).replace("{attribute}", attribute)
                    else:
                        condition+=f"GetSignal(\"{attribute}\").Value() && "
                        script+=ifscript.replace("{random_uuid}", random_uuid).replace("{attribute}", attribute)
                else:
                    condition+="("+attribute+") && "
            script=script.replace("{condition}", condition+"true")
            script=script.replace(random_uuid, condition+"true")
            script+="})()"+"\n</script>"
            final+=script
            continue
        if tokens[i]["type"]=="tag" and tokens[i]["value"]=="for":
            pass
        if tokens[i]["type"] in ["script", "style"]:
            tag=tokens[i]["type"]
            final+="\n<"+tag+">\n"+tokens[i]["value"]+"\n</"+tag+">"
            continue
        final+="\n"+tokens[i]["value"]+"\n"
    return final