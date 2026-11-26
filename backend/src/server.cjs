const express = require("express");
require("dotenv").config();

const app = express();

app.use(express.json());

const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || "127.0.0.1";

app.get("/", (req, res) => {
    res.json({
        application: "AeroEngine-Blockchain",
        status: "running"
    });
});

app.get("/api/health", (req, res) => {
    res.json({
        backend: "online",
        blockchain: "not_connected",
        channel: process.env.CHANNEL_NAME,
        chaincode: process.env.CHAINCODE_NAME
    });
});

app.listen(PORT, HOST, () => {
    console.log(`AeroEngine API running on http://${HOST}:${PORT}`);
});
