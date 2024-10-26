from os import PathLike
import uuid, json, base64, flask
from flask import send_from_directory, request, Flask
from urllib.parse import quote
import traceback

FlaskClass=Flask

def escapeString(a):
    return a.replace("\\", "\\\\").replace("\"", "\\\"").replace("'", "\\'").replace("\n", "\\n").replace("`", "\\`").replace("</script>", "</`+`script>").replace("<script>", "<`+`script>")

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
    def __init__(self, import_name, static_url_path = None, static_folder = "static", static_host = None, host_matching = False, subdomain_matching = False, template_folder = "templates", instance_path = None, instance_relative_config = False, root_path = None):
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
        resp=super().make_response(object)
        resp.headers["Cache-Control"]="no-cache, no-store, must-revalidate"
        resp.headers["Pragma"]="no-cache"
        resp.headers["Expires"]="0"
        return resp

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
    return response

def render(path, variables={}):
    tokenise=path.endswith(".html")
    try:
        component=open(path).read()
    except:
        component=open("components/"+path+".html").read()
        tokenise=True
    if tokenise:
        component=ssr(component, "py", variables)
        tokens=tokeniser(component)
        component="<body>\n"+compiler(tokens, variables).strip("\n")+"\n</body>"
        component=ssr(component, "post", variables)
    return Render(component)

def ssr(code, tag="py", variables={}):
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
        if buffer.endswith("<"+tag+">"):
            buffer=""
            while True:
                i+=1
                if i>=code_len:
                    break
                buffer+=code[i]
                if buffer.endswith("</"+tag+">"):
                    break
            uid=uuid.uuid4().__str__()
            pysegments[uid]=buffer[:len(buffer)-len(tag)-3]
            toreplace.append(["<"+tag+">"+buffer, uid])
            buffer=""
    for x in toreplace:
        code=str(code).replace(x[0], x[1], 1)
    for x in pysegments:
        try:
            to_evaluate=pysegments[x].strip(" \n\t\r")
            result=eval(to_evaluate, variables, variables)
            if type(result)!=str:
                if type(result)==Render:
                    result=result.render
                else:
                    result=json.dumps(result)
            code=str(code.replace(x, result))
        except:
            exec("result=None", variables, variables)
            base="\n".join([" "+x for x in pysegments[x].strip(" \r").split("\n")])
            if base!="":
                to_evaluate="def _():\n"+base+"\nresult=_()"
            exec(to_evaluate, variables, variables)
            if type(variables["result"])!=str:
                if type(variables["result"])==Render:
                    variables["result"]=variables["result"].render
                else:
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
        if not instring and x in " \n\t\r":
            if buffer!="":
                out.append({"type":"variable", "content":buffer})
                buffer=""
            continue
        if not instring and x in "=":
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
            count=1
            while True:
                i+=1
                if i>=code_len:
                    raise EOFError
                if code[i]=="<":
                    count+=1
                if code[i]==">":
                    count-=1
                if count==0:
                    break
                buffer+=code[i]
            args={}
            tokens=innertokeniser(buffer)
            name=tokens[0]["content"]
            tokens=tokens[1:]
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
                if True in set([buffer.endswith("<"+name+x) for x in [" ", "\n", "\t", "\r"]]) or buffer.endswith("<"+name+">"):
                    count+=1
                if count==0:
                    break
            buffer=buffer[:len(buffer)-len("</"+name+">")]
            if name not in ["script", "js", "post", "style"]:
                children=tokeniser(buffer)
            else:
                if name=="post":
                    min_spaces=9999999
                    for x in buffer.split("\n"):
                        if len(x.strip("\t \n\r"))!=0:
                            spaces=len(x)-len(str(x).lstrip(" \t"))
                            if spaces<min_spaces:
                                min_spaces=spaces
                    new_buffer=[]
                    for x in buffer.split("\n"):
                        new_buffer+=[x[min_spaces:]]
                    buffer="\n".join(new_buffer)
                children=buffer
            out.append({"type":"tag", "tag":name, "args":args, "children":children})
            buffer=""
            continue
        rawtext+=code[i]
    if rawtext!="":
        out.append({"type":"raw", "content":rawtext})
    return out

def compiler(tokens, variables={}):
    out=""
    for token in tokens:
        if token["type"]=="raw":
            token["content"]=token["content"].strip(" \t\n\r")
            if token["content"]=="":
                continue
            if token["content"][0]=="{" and token["content"][-1]=="}" and token["content"][1:-1] in variables:
                out+=token["content"]
                continue
            out+=f"""
<script>
(()=>{{
    const div=document.currentScript
    div.insertAdjacentText("afterend", "{escapeString(token["content"])}");
    const textNode = document.currentScript.nextSibling
    try {{
        AddNode(document.currentScript, document.currentScript.getAttribute("nodeTracker"))
        AddNode(textNode, document.currentScript.getAttribute("nodeTracker"))
    }} catch {{}}
}})()
</script>
"""
            continue
        if token["type"]=="tag" and token["tag"] not in ["js", "signal", "if", "for"]:
            script=""
            rendered_attributes=[]
            for attribute in token["args"]:
                if token["args"][attribute]!=True and "<js" in token["args"][attribute]:
                    to_render={}
                    raw_attributes=""
                    code=token["args"][attribute]
                    buffer=""
                    i=-1
                    code_len=len(code)
                    signals=[]
                    while True:
                        i+=1
                        if i>=code_len:
                            break
                        buffer+=code[i]
                        if buffer.endswith("<js"):
                            if len(buffer)>3:
                                raw_attributes+=buffer[:len(buffer)-3]
                            buffer=""
                            signals_string=""
                            while True:
                                i+=1
                                if i>=code_len:
                                    raise EOFError
                                signals_string+=code[i]
                                if signals_string.endswith(">"):
                                    signals_string=signals_string[:len(signals_string)-1]
                                    break
                            signals_string=signals_string.strip(" \r").replace("\t", " ")
                            code_buffer=""
                            while True:
                                i+=1
                                if i>=code_len:
                                    raise EOFError
                                code_buffer+=code[i]
                                if "</js>" in code_buffer:
                                    code_buffer=code_buffer[:len(code_buffer)-5]
                                    break
                            while "  " in signals_string:
                                signals_string=signals_string.replace("  ", " ")
                            signals+=signals_string.split() 
                            id=uuid.uuid4().__str__()
                            raw_attributes+=id
                            to_render[id]=f"""
                            callbacks.push(()=>{{
                                try {{
                                    var result=eval("{escapeString(code_buffer)}")
                                    if (result) {{
                                        return ["{id}", result]
                                    }}
                                }} catch {{}}
                                function _() {{
                                    {code_buffer}
                                }}
                                return ["{id}", _()]
                            }})
                            """
                            continue
                    if buffer!="":
                        raw_attributes+=buffer
                    script+=f"""
                        ((targetElement)=>{{
                            
                            var callbacks=[];
                            var signals={json.dumps(signals)};
                            var render=()=>{{
                                    var out="{raw_attributes.replace(chr(10), "")}";
                                    callbacks.forEach((y)=>{{
                                        try {{
                                            var res=y();
                                            out=out.replace(res[0], String(res[1]));
                                        }} catch (e) {{
                                            console.error(e)
                                        }}
                                    }})
                                    targetElement.setAttribute("{attribute}", out)
                                }}
                            signals.forEach((x)=>{{
                                OnChange(x, render)
                            }});
                            {chr(10).join([to_render[z] for z in to_render])}
                            render();
                        }})(document.currentScript.previousElementSibling);
                        """
                else:
                    if token["args"][attribute]==True:
                        rendered_attributes.append(attribute)
                    else:
                        rendered_attributes.append(attribute+"="+"\""+token["args"][attribute]+"\"")
            rendered_attributes=" ".join(rendered_attributes)
            if len(rendered_attributes)!=0:
                rendered_attributes=" "+rendered_attributes.strip()
            if token["tag"] in ["script", "post", "style"]:
                child_render=token["children"]
            else:
                child_render=compiler(token["children"])

            out+="<"+token["tag"]+rendered_attributes+">"
            exception_tags=["textarea"]
            if token["tag"] not in exception_tags:
                out+="\n"
            out+=child_render.strip(" \n")
            if token["tag"] not in exception_tags:
                out+="\n"
            out+="</"+token["tag"]+">"
            if script!="":
                out+="<script>\n"+script+"</script>\n"
            continue
        if token["type"]=="tag" and token["tag"]=="js":
            out+=f"""
            <script>
                (()=>{{
                    document.currentScript.insertAdjacentText("afterend", "")
                    var textNode=document.currentScript.nextSibling
                    try {{
                        var id=document.currentScript.getAttribute("nodeTracker")
                        AddNode(textNode, document.currentScript.getAttribute("nodeTracker"))
                    }} catch {{}}
                    function Render() {{
                        function _() {{
                            try {{
                                var result=eval("{escapeString(token["children"])}")
                                if (result !== undefined) {{
                                    return result
                                }}
                            }} catch {{}}
                            {token["children"]}
                        }}
                        var renderedText=_()
                        if (renderedText==undefined) {{
                            renderedText=""
                        }}
                        var renderedNode=document.createTextNode(String(renderedText))
                        try {{
                            AddNode(renderedNode, id)
                        }} catch {{}}
                        textNode.replaceWith(renderedNode)
                        textNode.remove()
                        textNode=renderedNode
                    }}
                    ({json.dumps([x for x in token["args"]])}).forEach((x)=>{{
                        OnChange(x, Render)
                    }})
                    Render()
                }})()
            </script>
            """
        if token["type"]=="tag" and token["tag"]=="signal":
            token["tag"]="if"
            token["args"]["condition"]="true"
        if token["type"]=="tag" and token["tag"]=="if":
            condition="true"
            condition_signals=[x for x in token["args"] if x!="condition"]
            if "condition" in token["args"]:
                condition=token["args"]["condition"]
            else:
                for x in token["args"]:
                    condition+=f""" && GetSignal("{x}").Value()"""
            out+="""
            <script>
            (()=>{
                var id=null;
                try {
                    id=document.currentScript.getAttribute("nodeTracker")
                    AddNode(document.currentScript, id)
                }  catch {}
                var self=document.currentScript
                var parentElement=document.currentScript.parentElement
                var html=`{html}`
                var lastUUID=null;
                function Remove() {
                    if (lastUUID!==null) {
                        RemoveNode(lastUUID)
                    }
                }
                function Render(html) {
                    var element=document.createElement("div")
                    try {
                        Remove()
                    } catch {}
                    if (id!==null && nodes[id]==undefined) {
                        throw ""
                    }
                    element.innerHTML=html
                    lastUUID=GenerateUUID();
                    nodes[lastUUID]=[];
                    if (id!==null) {
                        AddParent(lastUUID, id)
                    }
                    var ArrayA=Array.from(element.children)
                    if (Array.from(element.children)[0].tagName!="SCRIPT") {
                        ArrayA=ArrayA.reverse()
                    }
                    ArrayA.forEach((x)=>{
                        if (x.tagName=="SCRIPT") {
                            const newScript = document.createElement("script")
                            newScript.setAttribute("nodeTracker", lastUUID)
                            if (x.src) {
                                newScript.src = x.src
                            } else {
                                newScript.textContent = x.textContent
                            }
                            x.parentNode.replaceChild(newScript, x)
                            x=newScript
                        } else {
                            executeScripts(x)
                        }
                        try {
                            nodes[document.currentScript.getAttribute("nodeTracker")].push(x)
                        } catch {}
                        AddNode(x, lastUUID)
                        self.insertAdjacentElement("afterend", x)
                    })
                }
                if ({condition}) {
                    Render(html)
                }
                ({condition_signals}).forEach((x)=>{
                    OnChange(x, ()=>{
                        if ({condition}) {
                            Render(html)
                        } else {
                            try {
                                Remove()
                            } catch {}
                        }
                    })
                })
            })()
            </script>
            """.replace("{signals}", json.dumps([x for x in token["args"]])).replace("{html}", escapeString(compiler(token["children"]))).replace("{condition_signals}", json.dumps(condition_signals)).replace("{condition}", condition)
            continue
    return out