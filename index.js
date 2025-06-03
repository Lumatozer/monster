var state = {}

export class Signal {
    constructor(signalID, defaultValue) {
        return [defaultValue, (value) => Signal.setValue(signalID, value)]
    }

    static setValue(signalID, value) {
        state[signalID]["value"] = value
        Object.values(state[signalID]["callbacks"]).forEach((x) => x(value))
    }

    static onChange(signalID, callback, callbackName, defaultValue) {
        if (state[signalID]) {
            state[signalID]["callbacks"][callbackName]=callback
        } else {
            state[signalID] = {
                "value": defaultValue,
                "callbacks": {}
            }
            state[signalID]["callbacks"][callbackName]=callback
        }
    }
}