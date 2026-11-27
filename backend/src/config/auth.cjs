const config = {
    secret: process.env.JWT_SECRET,
    issuer: "aeroengine-backend",
    audience: "aeroengine-client",
    expiresIn: "1h"
};

const users = Object.freeze([
    {
        username: "airline",
        organization: "Org1MSP",
        role: "airline",
        passwordHash: process.env.ORG1_PASSWORD_HASH
    },
    {
        username: "maintenance",
        organization: "Org2MSP",
        role: "maintenance",
        passwordHash: process.env.ORG2_PASSWORD_HASH
    }
]);

if (!config.secret || config.secret.length < 64) {
    throw new Error("Invalid or missing JWT_SECRET");
}

if (users.some(user => !user.passwordHash)) {
    throw new Error("Missing authentication password hashes");
}

function findUser(username) {
    return users.find(user => user.username === username);
}

function publicUser(user) {
    return {
        username: user.username,
        organization: user.organization,
        role: user.role
    };
}

module.exports = { config, users, findUser, publicUser };
