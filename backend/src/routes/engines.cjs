const express = require("express");

const router = express.Router();

function pendingTransaction(functionName) {
    return (req, res) => {
        res.status(503).json({
            error: "Blockchain integration not ready",
            chaincodeFunction: functionName
        });
    };
}

router.post("/", pendingTransaction("RegisterEngine"));

router.get("/", pendingTransaction("GetAllEngines"));

router.get("/:id", pendingTransaction("ReadEngine"));

router.post("/:id/maintenance/request",
    pendingTransaction("RequestMaintenance"));

router.post("/:id/maintenance",
    pendingTransaction("RecordMaintenance"));

router.patch("/:id/status",
    pendingTransaction("UpdateEngineStatus"));

router.post("/:id/transfer",
    pendingTransaction("TransferEngine"));

router.get("/:id/history",
    pendingTransaction("GetEngineHistory"));

router.get("/:id/maintenance",
    pendingTransaction("GetMaintenanceHistory"));

module.exports = router;
