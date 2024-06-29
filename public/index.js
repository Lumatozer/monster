var a = Signal("a", true)

setInterval(()=>{
    a.setValue(!a.Value())
}, 100)