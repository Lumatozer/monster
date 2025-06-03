var state = {}

export class Signal {

    constructor (signalID, defaultValue) {
        return [defaultValue, (value) => Signal.setValue(signalID, value)]
    }

    static setValue(signalID, value) {
        state[signalID]["value"] = value
        Object.values(state[signalID]["callbacks"]).forEach((x) => x(value))
    }

    static onChange(signalID, callbackID, callback, defaultValue) {
        if (state[signalID]) {
            state[signalID]["callbacks"][callbackID]=callback
        } else {
            state[signalID] = {
                "value": defaultValue,
                "callbacks": {}
            }

            state[signalID]["callbacks"][callbackID]=callback
        }
    }

    static defaultValue (signalID, defaultValue) {
        if (state[signalID]) {
            return state[signalID]["value"]
        }
        return defaultValue
    }

    static removeListener(signalID, callbackID) {
        delete state[signalID]["callbacks"][callbackID]
    }

    static generateUUID() {
        const chars = '0123456789abcdefghijklmnopqrstuvwxyz';
        const array = crypto.getRandomValues(new Uint8Array(64));

        return Array.from(array, x => chars[x % 36]).join('');
    }
}