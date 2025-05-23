var signals={}
var callbacks={}
var nodes={}
var parents={}

function AddParent(id, parent) {
    parents[id]=parent
}

function AddNode(element, id) {
    var current=nodes[id]
    while (current) {
        current.push(element)
        id=parents[id]
        current=nodes[id]
    }
}

function RemoveNode(id) {
    if (id==undefined) {
        return
    }
    nodes[id].forEach((x)=>{
        x.remove()
    })
    delete nodes[id]
    var toremove=[]
    for (let index = 0; index < Object.keys(parents).length; index++) {
        const element = Object.keys(parents)[index]
        if (parents[element]===id) {
            toremove.push(element)
            RemoveNode(element)
        }
    }
    toremove.forEach((x)=>{
        delete parents[x]
    })
}

function Signal(id, value) {
    if (id == undefined) {
        throw "id cannot be undefined";
    }
    signals[id] = {
        "Value": () => value,
        "setValue": async (value) => {
            signals[id]["Value"] = () => value;
            var newCallbacks = [];
            for (var i = callbacks[id].length - 1; i >= 0; i--) {
                try {
                    await callbacks[id][i]();
                    newCallbacks.unshift(callbacks[id][i]);
                } catch (e) {
                    console.error(e);
                }
            }
            callbacks[id] = newCallbacks;
        }
    };
    if (callbacks[id] === undefined) {
        callbacks[id] = [];
    }
    return signals[id];
}

function OnChange(id, callback) {
    if (callbacks[id] === undefined) {
        callbacks[id] = [];
    }
    callbacks[id].push(callback);
}

function DerivedFrom(id, value, dependsOn) {
    if (id == undefined) {
        throw "id cannot be undefined";
    }
    signals[id] = { "Value": value };
    if (callbacks[id] === undefined) {
        callbacks[id] = [];
    }
    dependsOn.forEach((x) => {
        if (callbacks[x] === undefined) {
            callbacks[x] = [];
        }
        callbacks[x].push(async (y) => {
            var newCallbacks = [];
            for (var i = callbacks[id].length - 1; i >= 0; i--) {
                try {
                    await callbacks[id][i]();
                    newCallbacks.unshift(callbacks[id][i]);
                } catch (e) {
                    console.error(e);
                }
            }
            callbacks[id] = newCallbacks;
        });
    });
    return signals[id];
}

function GetSignal(id) {
    return signals[id]
}

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

function GenerateUUID() {
    const array = new Uint8Array(16);
    crypto.getRandomValues(array);
    array[6] = (array[6] & 0x0f) | 0x40;
    array[8] = (array[8] & 0x3f) | 0x80;
    const hexArray = [...array].map(b => b.toString(16).padStart(2, '0'));
    return [
      hexArray.slice(0, 4).join(''),
      hexArray.slice(4, 6).join(''),
      hexArray.slice(6, 8).join(''),
      hexArray.slice(8, 10).join(''),
      hexArray.slice(10, 16).join('')
    ].join('-');
  }