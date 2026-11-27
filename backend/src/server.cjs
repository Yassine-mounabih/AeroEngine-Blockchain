require("dotenv").config();

const express = require("express");
const helmet = require("helmet");

const authRoutes = require("./routes/auth.cjs");
const engineRoutes = require("./routes/engines.cjs");
const { authenticate } = require("./middleware/auth.cjs");

const app = express();

app.disable("x-powered-by");
app.use(helmet());
app.use(express.json({ limit: "256kb" }));

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

app.use("/auth", authRoutes);

app.get("/auth/me", authenticate, (req, res) => {
    res.json({ user: req.user });
});

app.use("/engines", authenticate, engineRoutes);

app.use((req, res) => {
    res.status(404).json({
        error: "Endpoint not found"
    });
});

app.use((err, req, res, next) => {
    if (err.type === "entity.parse.failed") {
        return res.status(400).json({
            error: "Invalid JSON"
        });
    }

    if (err.type === "entity.too.large") {
        return res.status(413).json({
            error: "Request body too large"
        });
    }

    console.error("Internal request error");
    res.status(500).json({
        error: "Internal server error"
    });
});

const server = app.listen(PORT, HOST, () => {
    console.log(`AeroEngine API running on http://${HOST}:${PORT}`);
});

server.on("error", (err) => {
    console.error(`Server startup failed: ${err.code}`);
    process.exit(1);
});
