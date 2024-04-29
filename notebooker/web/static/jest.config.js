module.exports = {
    setupFiles: ["./jest.setup.js"],
    reporters: [
        "default",
        ["jest-junit", { "outputDirectory": "./test-results/jest" }]
    ]
};
