const jwt = require("jsonwebtoken");

const {
    config,
    findUser,
    publicUser
} = require("../config/auth.cjs");

function authenticate(req, res, next) {
    const authorization = req.headers.authorization || "";
    const match = /^Bearer ([^\s]+)$/i.exec(authorization);

    if (!match) {
        return res.status(401).json({
            error: "Authentication required"
        });
    }

    try {
        const decoded = jwt.verify(match[1], config.secret, {
            algorithms: ["HS256"],
            issuer: config.issuer,
            audience: config.audience
        });

        const user = findUser(decoded.sub);

        if (!user) {
            return res.status(401).json({
                error: "Unknown user"
            });
        }

        req.user = publicUser(user);
        next();

    } catch {
        return res.status(401).json({
            error: "Invalid or expired token"
        });
    }
}

module.exports = { authenticate };
