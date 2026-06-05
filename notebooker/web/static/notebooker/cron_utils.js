// Wrapper around croner (loaded via CDN) that translates APScheduler day-of-week
// convention to croner's convention before parsing.
//
// APScheduler from_crontab uses Python weekday(): 0=Mon, 1=Tue, ..., 6=Sun
// croner (standard crontab) uses:                 0=Sun, 1=Mon, ..., 6=Sat
// Conversion: croner_value = (apscheduler_value + 1) % 7

function _convertDowValue(v) {
    const n = parseInt(v, 10);
    if (isNaN(n) || n < 0 || n > 6) throw new Error("Invalid day-of-week value: " + v);
    return ((n + 1) % 7).toString();
}

function _convertDowRange(part) {
    if (part === "*") return "*";
    if (part.includes("-")) {
        const [a, b] = part.split("-");
        const na = parseInt(a, 10);
        const nb = parseInt(b, 10);
        if (isNaN(na) || na < 0 || na > 6) throw new Error("Invalid day-of-week value: " + a);
        if (isNaN(nb) || nb < 0 || nb > 6) throw new Error("Invalid day-of-week value: " + b);
        const ca = (na + 1) % 7;
        const cb = (nb + 1) % 7;
        if (ca <= cb) return ca + "-" + cb;
        // Range wraps in croner space (e.g. APSched 4-6 Fri-Sun → croner 5,6,0)
        const values = [];
        for (let i = na; i <= nb; i++) values.push(((i + 1) % 7).toString());
        return values.join(",");
    }
    return _convertDowValue(part);
}

function _convertDowField(field) {
    if (field === "*") return "*";
    return field.split(",").map(part => {
        if (part.includes("/")) {
            const [range, step] = part.split("/");
            if (range === "*") {
                // Expand */N to explicit values so the Monday-origin is preserved.
                const s = parseInt(step);
                const values = [];
                for (let i = 0; i < 7; i += s) values.push(_convertDowValue(i));
                return values.join(",");
            }
            return _convertDowRange(range) + "/" + step;
        }
        return _convertDowRange(part);
    }).join(",");
}

function parseExpression(expr) {
    if (typeof Cron === "undefined") {
        throw new Error("croner library not loaded");
    }
    const fields = expr.trim().split(/\s+/);
    if (fields.length !== 5) throw new Error("Expected 5 fields");

    const [minute, hour, dom, month, dow] = fields;
    const converted = [minute, hour, dom, month, _convertDowField(dow)].join(" ");

    const job = new Cron(converted);
    return {
        next() {
            const d = job.nextRun();
            if (!d) throw new Error("No matching date found");
            return d;
        }
    };
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = { parseExpression, _convertDowField };
} else if (typeof window !== "undefined") {
    window.parseExpression = parseExpression;
}
