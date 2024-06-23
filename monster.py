import uuid, json
from flask import send_from_directory

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

def init(app):
    @app.route('/<path:path>')
    def catch_all(path):
        return set_headers(send_from_directory("public", path), path)