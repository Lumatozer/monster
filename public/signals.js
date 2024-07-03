var signals={}
var callbacks={}

function Signal(id, value) {
    if (id==undefined) {
        throw "id cannot be undefined"
    }
    signals[id]={"Value":()=>value, "setValue":async (value)=>{
        signals[id]["Value"]=()=>value
        var newCallbacks=[]
        for (var i=0; i<callbacks[id].length; i++) {
            try {
                await callbacks[id][i]()
                newCallbacks.push(callbacks[id][i])
            } catch {}
        }
        callbacks[id]=newCallbacks
    }}
    if (callbacks[id]===undefined) {
        callbacks[id]=[]
    }
    return signals[id]
}

function OnChange(id, callback) {
    callbacks[id].push(callback)
}

function DerivedFrom(id, value, dependsOn) {
    if (id==undefined) {
        throw "id cannot be undefined"
    }
    signals[id]={"Value":value}
    if (callbacks[id]===undefined) {
        callbacks[id]=[]
    }
    dependsOn.forEach((x)=>{
        callbacks[x].push(async (y)=>{
            var newCallbacks=[]
            for (var i=0; i<callbacks[id].length; i++) {
                try {
                    await callbacks[id][i]()
                    newCallbacks.push(callbacks[id][i])
                } catch {}
            }
            callbacks[id]=newCallbacks
        })
    })
    return signals[id]
}

function GetSignal(id) {
    return signals[id]
}