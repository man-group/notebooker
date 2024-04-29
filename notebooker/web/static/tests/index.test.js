/**
 * @jest-environment jsdom
 */
const { JSDOM } = require("jsdom");
const $ = require("jquery");
const { updateNavigationPanel, updateContents, load_data, getCurrentFolder } = require("../notebooker/index.js");

const dom = new JSDOM();
global.window = dom.window;
global.document = window.document;
global.fetch = jest.fn();

describe("index.js", () => {
    beforeEach(() => {
        delete window.location;
        window.location = { pathname: "/folder/test/my%20fake%20folder/hello" };
        $("body").html('<div id="folderNavigationPanel"></div><div id="cardContainer"></div>');
        fetch.mockClear();
    });

    test("getCurrentFolder", () => {
        expect(getCurrentFolder()).toBe("test/my fake folder/hello/");
    });

    test("updateNavigationPanel", () => {
        updateNavigationPanel("test/");
        expect($("#folderNavigationPanel").html()).toContain("test");
    });

    test("updateContents", () => {
        const entries = {};
        entries["report"] = {
            report_name: "report",
            time_diff: "1 hour",
            count: 1,
            scheduler_runs: 1,
        };
        entries["hello/world"] = {
            report_name: "hello/world",
            time_diff: "1 second",
            count: 2,
            scheduler_runs: 1,
        };
        entries["folder with spaces/ and again/ and one more /test"] = {
            report_name: "folder with spaces/ and again/ and one more /test",
            time_diff: "1 second",
            count: 2,
            scheduler_runs: 1,
        };
        updateContents("", entries);
        const cardContainer = $("#cardContainer").html();
        expect(cardContainer).toContain('href="/result_listing/report"');
        expect(cardContainer).toContain('href="/folder/hello"');
        expect(cardContainer).toContain('href="/folder/folder with spaces"');
    });

    test("load_data", async () => {
        let mockResult = {};
        mockResult["test/my fake folder/hello/report"] = {
            report_name: "test/my fake folder/hello/report",
            time_diff: "1 hour",
            count: 1,
            scheduler_runs: 1,
        };
        fetch.mockResolvedValueOnce({
            json: () => Promise.resolve(mockResult),
        });
        await load_data();
        expect(fetch).toHaveBeenCalledWith("/core/get_all_templates_with_results/folder/test/my fake folder/hello/");
        expect($("#folderNavigationPanel").html()).toContain(
            '<a href="/folder/test/my fake folder">my fake folder </a>'
        );
        expect($("#cardContainer").html()).toContain("report");
    });
});
