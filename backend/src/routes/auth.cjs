const express = require("express");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const { rateLimit } = require("express-rate-limit");

const {
    config,
    users,
    findUser,
    publicUser
} = require("../config/auth.cjs");

const router = express.Router();

const loginLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    limit: 10,
    standardHeaders: "draft-7",
    legacyHeaders: false,
    message: {
        error: "Too many login attempts. Try again later."
    }
});

router.post("/login", loginLimiter, async (req, res) => {
    const { username, password } = req.body || {};

    if (
        typeof username !== "string" ||
        typeof password !== "string" ||
        !username ||
        !password ||
        Buffer.byteLength(password, "utf8") > 72
    ) {
        return res.status(400).json({
            error: "Valid username and password are required"
        });
    }

    const user = findUser(username);

    const valid = await bcrypt.compare(
        password,
        user ? user.passwordHash : users[0].passwordHash
    );

    if (!user || !valid) {
        return res.status(401).json({
            error: "Invalid username or password"
        });
    }

    const token = jwt.sign(
        {},
        config.secret,
        {
            algorithm: "HS256",
            subject: user.username,
            issuer: config.issuer,
            audience: config.audience,
            expiresIn: config.expiresIn
        }
    );

    res.set("Cache-Control", "no-store");

    return res.json({
        token,
        tokenType: "Bearer",
        expiresIn: 3600,
        user: publicUser(user)
    });
});

module.exports = router;
