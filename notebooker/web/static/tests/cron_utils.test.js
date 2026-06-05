const croner = require("croner");
global.Cron = croner.Cron || croner;

const { parseExpression, _convertDowField } = require("../notebooker/cron_utils");

describe("_convertDowField", () => {
    test("wildcard passes through", () => {
        expect(_convertDowField("*")).toBe("*");
    });

    test("0 (APSched Mon) -> 1 (croner Mon)", () => {
        expect(_convertDowField("0")).toBe("1");
    });

    test("6 (APSched Sun) -> 0 (croner Sun)", () => {
        expect(_convertDowField("6")).toBe("0");
    });

    test("range 0-4 (Mon-Fri) -> 1-5", () => {
        expect(_convertDowField("0-4")).toBe("1-5");
    });

    test("range 1-5 (Tue-Sat in APSched) -> 2-6", () => {
        expect(_convertDowField("1-5")).toBe("2-6");
    });

    test("comma list 0,2,4 -> 1,3,5", () => {
        expect(_convertDowField("0,2,4")).toBe("1,3,5");
    });

    test("*/2 expands and shifts from Monday", () => {
        // APSched */2 from Mon (0): 0,2,4,6 = Mon,Wed,Fri,Sun -> croner 1,3,5,0
        expect(_convertDowField("*/2")).toBe("1,3,5,0");
    });

    test("*/3 expands and shifts from Monday", () => {
        // APSched */3 from Mon (0): 0,3,6 = Mon,Thu,Sun -> croner 1,4,0
        expect(_convertDowField("*/3")).toBe("1,4,0");
    });

    test("range 4-6 (Fri-Sun) wraps -> 5,6,0", () => {
        expect(_convertDowField("4-6")).toBe("5,6,0");
    });

    test("range 0-6 (Mon-Sun, all days) wraps -> 1,2,3,4,5,6,0", () => {
        expect(_convertDowField("0-6")).toBe("1,2,3,4,5,6,0");
    });

    test("throws on value > 6", () => {
        expect(() => _convertDowField("7")).toThrow("Invalid day-of-week value: 7");
    });

    test("throws on large DOW value", () => {
        expect(() => _convertDowField("11231231231231233312312313123")).toThrow("Invalid day-of-week value");
    });
});

describe("parseExpression", () => {
    describe("invalid input", () => {
        test("throws on fewer than 5 fields", () => {
            expect(() => parseExpression("* * * *")).toThrow("Expected 5 fields");
        });

        test("throws on more than 5 fields", () => {
            expect(() => parseExpression("* * * * * *")).toThrow("Expected 5 fields");
        });

        test("throws on empty string", () => {
            expect(() => parseExpression("")).toThrow("Expected 5 fields");
        });

        test("throws on whitespace-only string", () => {
            expect(() => parseExpression("   ")).toThrow("Expected 5 fields");
        });

        test("throws on invalid expression", () => {
            expect(() => parseExpression("abc def ghi jkl mno")).toThrow();
        });

        test("throws on out-of-range DOW value", () => {
            expect(() => parseExpression("1 1 19 1 11231231231231233312312313123")).toThrow("Invalid day-of-week value");
        });

        test("throws on DOW value 7", () => {
            expect(() => parseExpression("0 9 * * 7")).toThrow("Invalid day-of-week value: 7");
        });
    });

    describe("next() returns a Date strictly in the future", () => {
        const expressions = [
            "* * * * *",
            "0 9 * * *",
            "30 14 * * 4",
            "*/15 * * * *",
            "0 12 * * 0-4",
        ];
        test.each(expressions)("%s returns a future date", (expr) => {
            const result = parseExpression(expr).next();
            expect(result).toBeInstanceOf(Date);
            expect(result.getTime()).toBeGreaterThan(Date.now());
        });

        test("* * * * * is at most 1 minute away", () => {
            const result = parseExpression("* * * * *").next();
            expect(result.getTime() - Date.now()).toBeLessThanOrEqual(61000);
        });
    });

    describe("minute / hour fields (unchanged by DOW conversion)", () => {
        test("specific minute", () => {
            expect(parseExpression("30 * * * *").next().getMinutes()).toBe(30);
        });

        test("*/15 matches 0, 15, 30, or 45", () => {
            expect([0, 15, 30, 45]).toContain(parseExpression("*/15 * * * *").next().getMinutes());
        });

        test("range 10-20", () => {
            const m = parseExpression("10-20 * * * *").next().getMinutes();
            expect(m).toBeGreaterThanOrEqual(10);
            expect(m).toBeLessThanOrEqual(20);
        });

        test("comma list 5,10,15", () => {
            expect([5, 10, 15]).toContain(parseExpression("5,10,15 * * * *").next().getMinutes());
        });

        test("specific hour with minute 0", () => {
            const result = parseExpression("0 9 * * *").next();
            expect(result.getHours()).toBe(9);
            expect(result.getMinutes()).toBe(0);
        });

        test("*/6 hours matches 0, 6, 12, or 18", () => {
            expect([0, 6, 12, 18]).toContain(parseExpression("0 */6 * * *").next().getHours());
        });
    });

    describe("day-of-week (APScheduler convention: 0=Mon, 1=Tue, ..., 6=Sun)", () => {
        test("0 (Monday) returns a Monday", () => {
            expect(parseExpression("0 9 * * 0").next().getDay()).toBe(1); // JS Mon=1
        });

        test("1 (Tuesday) returns a Tuesday", () => {
            expect(parseExpression("0 9 * * 1").next().getDay()).toBe(2); // JS Tue=2
        });

        test("4 (Friday) returns a Friday", () => {
            expect(parseExpression("0 9 * * 4").next().getDay()).toBe(5); // JS Fri=5
        });

        test("6 (Sunday) returns a Sunday", () => {
            expect(parseExpression("0 0 * * 6").next().getDay()).toBe(0); // JS Sun=0
        });

        test("0-4 (Mon-Fri) returns a weekday", () => {
            const day = parseExpression("0 9 * * 0-4").next().getDay();
            expect(day).toBeGreaterThanOrEqual(1); // JS Mon
            expect(day).toBeLessThanOrEqual(5);    // JS Fri
        });

        test("0,2,4 (Mon/Wed/Fri) returns one of those days", () => {
            expect([1, 3, 5]).toContain(parseExpression("0 9 * * 0,2,4").next().getDay());
        });
    });

    describe("month and day-of-month fields", () => {
        test("specific month", () => {
            expect(parseExpression("0 0 1 6 *").next().getMonth() + 1).toBe(6);
        });

        test("0 0 1 * * returns 1st of the month", () => {
            expect(parseExpression("0 0 1 * *").next().getDate()).toBe(1);
        });
    });

    describe("combined expressions", () => {
        test("0 9 * * 0-4 returns a weekday (Mon-Fri) at 09:00", () => {
            const result = parseExpression("0 9 * * 0-4").next();
            expect(result.getDay()).toBeGreaterThanOrEqual(1);
            expect(result.getDay()).toBeLessThanOrEqual(5);
            expect(result.getHours()).toBe(9);
            expect(result.getMinutes()).toBe(0);
        });

        test("*/5 * * * * returns minute divisible by 5", () => {
            expect(parseExpression("*/5 * * * *").next().getMinutes() % 5).toBe(0);
        });

        test("* * 1 2 0-6 (all days, Feb 1) does not throw", () => {
            expect(parseExpression("* * 1 2 0-6").next()).toBeInstanceOf(Date);
        });

        test("0 9 * * 4-6 (Fri-Sun) returns a Fri, Sat, or Sun", () => {
            expect([5, 6, 0]).toContain(parseExpression("0 9 * * 4-6").next().getDay());
        });
    });
});
