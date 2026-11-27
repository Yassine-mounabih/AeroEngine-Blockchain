# AeroEngine-Blockchain — API Contract

**Version:** Draft 0.1  
**Prepared:** 2026-11-27  
**Status:** Draft for review by both project members. This document is not yet an approved implementation contract.

> This document consolidates the currently agreed project configuration, the existing Go model JSON tags, the nine REST routes, and the proposed workflow rules. It deliberately labels unresolved choices instead of silently changing the agreed architecture. The chaincode and backend are still under development; examples below describe the intended contract, not a claim that every endpoint already exists.

## 1. Project configuration

| Setting | Agreed value |
|---|---|
| Project | `AeroEngine-Blockchain` |
| Channel | `mychannel` |
| Chaincode | `aeroengine` |
| Org1 MSP | `Org1MSP` — airline company |
| Org2 MSP | `Org2MSP` — maintenance company |
| Chaincode language | Go |
| Backend | Node.js / Express, port `3000` |
| Frontend | Python / Streamlit, port `8502` |
| Backend SDK | `@hyperledger/fabric-gateway` (currently declared as `^1.13.0`) |
| gRPC package | `@grpc/grpc-js` |

The Streamlit frontend calls the Node.js backend. It must not connect directly to Fabric or possess Fabric private keys.

The intended chaincode endorsement policy for state-changing operations is:

```text
AND('Org1MSP.peer','Org2MSP.peer')
```

This policy requires endorsements from both peer organizations. It is separate from the submitting-client MSP authorization enforced by chaincode.

## 2. Chaincode transaction contract

All functions are methods of `SmartContract` and receive `contractapi.TransactionContextInterface` as their first argument. The argument names and order below are the agreed baseline from the project design.

| # | Chaincode method signature | Arguments after `ctx` | Gateway use | Authorized client |
|---:|---|---|---|---|
| 1 | `RegisterEngine(ctx contractapi.TransactionContextInterface, inputJSON string) (*Engine, error)` | One JSON-serialized `RegisterEngineInput` | `submitTransaction` | Org1 |
| 2 | `ReadEngine(ctx contractapi.TransactionContextInterface, engineID string) (*Engine, error)` | `engineID` | `evaluateTransaction` | Org1, Org2 |
| 3 | `GetAllEngines(ctx contractapi.TransactionContextInterface) ([]*Engine, error)` | None | `evaluateTransaction` | Org1, Org2 |
| 4 | `RequestMaintenance(ctx contractapi.TransactionContextInterface, inputJSON string) (*MaintenanceRequest, error)` | One JSON-serialized `RequestMaintenanceInput` | `submitTransaction` | Org1 |
| 5 | `RecordMaintenance(ctx contractapi.TransactionContextInterface, inputJSON string) (*MaintenanceRecord, error)` | One JSON-serialized `RecordMaintenanceInput` | `submitTransaction` | Org2 |
| 6 | `UpdateEngineStatus(ctx contractapi.TransactionContextInterface, engineID, newStatus, reason, evidenceHash string) (*Engine, error)` | Four individual strings, in this exact order | `submitTransaction` | Conditional: Org1 or Org2, according to status and custody rules |
| 7 | `TransferEngine(ctx contractapi.TransactionContextInterface, engineID, targetMSP, referenceID string) (*CustodyTransferRecord, error)` | Three individual strings, in this exact order | `submitTransaction` | Conditional: Org1 or Org2, according to transfer direction |
| 8 | `GetEngineHistory(ctx contractapi.TransactionContextInterface, engineID string) ([]*EngineHistoryEntry, error)` | `engineID` | `evaluateTransaction` | Org1, Org2 |
| 9 | `GetMaintenanceHistory(ctx contractapi.TransactionContextInterface, engineID string) ([]*MaintenanceRecord, error)` | `engineID` | `evaluateTransaction` | Org1, Org2 |

### Argument serialization rules

- Complex request objects are passed to chaincode as **one serialized JSON string**: `RegisterEngine`, `RequestMaintenance`, and `RecordMaintenance`.
- Simple scalar arguments are passed individually as strings, in the exact order shown above.
- `GetAllEngines` has no arguments after `ctx`.
- The backend should construct the serialized JSON using `JSON.stringify()` and pass it as one Gateway transaction argument. The chaincode decodes it strictly and rejects unknown fields.
- For routes containing `:id`, the path parameter is authoritative. The backend should inject that ID into the serialized chaincode input where the Go input struct requires `engineId`; it should not trust a conflicting body value.

### Submit versus evaluate

Use `submitTransaction()` for operations that write ledger state and `evaluateTransaction()` for read-only queries. Do not submit a query merely to read it, and do not evaluate a state-changing operation expecting it to commit.

## 3. Exact persisted JSON entity schemas

The JSON names below follow the Go struct tags. No fields currently use `omitempty`; persisted objects therefore serialize all declared fields. Optional string values should be represented as `""`, and optional slice values should be initialized as `[]` rather than `null` in responses.

### 3.1 Engine

| JSON field | JSON type | Required in persisted record | Meaning / source |
|---|---|---:|---|
| `docType` | string | Yes | Constant `ENGINE` |
| `engineId` | string | Yes | Unique engine identifier |
| `manufacturer` | string | Yes | Manufacturer |
| `model` | string | Yes | Engine model |
| `serialNumber` | string | Yes | Globally unique serial number within this channel |
| `aircraftMsn` | string | Yes | Aircraft manufacturer serial number, empty if not assigned |
| `aircraftRegistration` | string | Yes | Aircraft registration, empty if not assigned |
| `manufactureDate` | string | Yes | `YYYY-MM-DD` |
| `totalFlightMinutes` | integer | Yes | Non-negative; cannot decrease on later updates |
| `totalFlightCycles` | integer | Yes | Non-negative; cannot decrease on later updates |
| `operatorMsp` | string | Yes | Set by chaincode to `Org1MSP` |
| `custodianMsp` | string | Yes | Current physical custodian, initially `Org1MSP` |
| `operationalStatus` | string | Yes | `SERVICEABLE`, `UNSERVICEABLE`, or `RETIRED` |
| `maintenanceStatus` | string | Yes | `NONE`, `REQUESTED`, `AWAITING_MAINTENANCE_START`, `IN_PROGRESS`, `AWAITING_PARTS`, or `COMPLETED` |
| `activeMaintenanceRequestId` | string | Yes | Empty when no active request |
| `lastMaintenanceRequestId` | string | Yes | Empty before the first request |
| `lastMaintenanceRecordId` | string | Yes | Empty before the first maintenance record |
| `location` | string | Yes | Current recorded location; may be empty |
| `statusReason` | string | Yes | Reason for the latest status change; may be empty |
| `statusEvidenceHash` | string | Yes | SHA-256 evidence hash for latest status change; may be empty |
| `createdAt` | string | Yes | Fabric transaction timestamp, RFC3339 UTC |
| `updatedAt` | string | Yes | Fabric transaction timestamp, RFC3339 UTC |
| `createdBy` | string | Yes | Authenticated Fabric client identity ID |
| `updatedBy` | string | Yes | Authenticated Fabric client identity ID |

### 3.2 MaintenanceRequest

| JSON field | JSON type | Required in persisted record | Meaning / source |
|---|---|---:|---|
| `docType` | string | Yes | Constant `MAINTENANCE_REQUEST` |
| `requestId` | string | Yes | Unique request ID supplied by Org1 |
| `engineId` | string | Yes | Engine being maintained |
| `requestedByMsp` | string | Yes | Set by chaincode from caller MSP (`Org1MSP`) |
| `requestedBy` | string | Yes | Authenticated Fabric client identity ID |
| `assignedToMsp` | string | Yes | Set by chaincode to `Org2MSP` |
| `reason` | string | Yes | Reason for maintenance |
| `workScope` | string array | Yes | One or more requested work items |
| `priority` | string | Yes | `NORMAL`, `HIGH`, or `AOG` |
| `supportingEvidenceHashes` | string array | Yes | SHA-256 hashes; may be empty |
| `status` | string | Yes | `REQUESTED`, `IN_PROGRESS`, or `COMPLETED` |
| `requestedAt` | string | Yes | Fabric transaction timestamp, RFC3339 UTC |
| `updatedAt` | string | Yes | Latest Fabric transaction timestamp, RFC3339 UTC |
| `completedAt` | string | Yes | Empty until completed |

### 3.3 PartReplacement

| JSON field | JSON type | Required when an item exists | Meaning |
|---|---|---:|---|
| `partNumber` | string | Yes | Part number |
| `removedSerialNumber` | string | Yes | Serial number of removed part; empty if not applicable |
| `installedSerialNumber` | string | Yes | Serial number of installed part; empty if not applicable |

### 3.4 MaintenanceRecord

| JSON field | JSON type | Required in persisted record | Meaning / source |
|---|---|---:|---|
| `docType` | string | Yes | Constant `MAINTENANCE_RECORD` |
| `recordId` | string | Yes | Unique record ID supplied by Org2 |
| `requestId` | string | Yes | Existing active maintenance request |
| `engineId` | string | Yes | Engine being maintained |
| `providerMsp` | string | Yes | Set by chaincode to `Org2MSP` |
| `technicianReference` | string | Yes | Technician reference supplied by Org2; not a Fabric identity ID |
| `workOrderReference` | string | Yes | Maintenance work-order reference |
| `maintenanceType` | string | Yes | Type of maintenance performed |
| `findings` | string | Yes | Findings |
| `actionsPerformed` | string | Yes | Work performed |
| `partsReplaced` | array of `PartReplacement` | Yes | May be empty |
| `flightMinutesAtMaintenance` | integer | Yes | Non-negative and not less than engine's previous total |
| `flightCyclesAtMaintenance` | integer | Yes | Non-negative and not less than engine's previous total |
| `outcome` | string | Yes | `SERVICEABLE` or `UNSERVICEABLE` |
| `workCompletedAt` | string | Yes | Claimed physical completion time, RFC3339 |
| `evidenceHashes` | string array | Yes | SHA-256 hashes; may be empty subject to final policy |
| `regulatoryReferences` | string array | Yes | Applicable references; may be empty |
| `recordedAt` | string | Yes | Fabric transaction timestamp, RFC3339 UTC |
| `recordedBy` | string | Yes | Authenticated Fabric client identity ID |
| `transactionId` | string | Yes | Fabric transaction ID |

### 3.5 CustodyTransferRecord

| JSON field | JSON type | Required in persisted record | Meaning / source |
|---|---|---:|---|
| `docType` | string | Yes | Constant `CUSTODY_TRANSFER` |
| `transferId` | string | Yes | Recommended: derive from Fabric transaction ID to avoid caller-supplied collisions |
| `engineId` | string | Yes | Engine being transferred |
| `fromMsp` | string | Yes | Previous custodian MSP |
| `toMsp` | string | Yes | New custodian MSP |
| `referenceId` | string | Yes | Maintenance request ID or completed maintenance record ID, according to direction |
| `transferredBy` | string | Yes | Authenticated Fabric client identity ID |
| `transferredAt` | string | Yes | Fabric transaction timestamp, RFC3339 UTC |
| `transactionId` | string | Yes | Fabric transaction ID |

### 3.6 EngineHistoryEntry

| JSON field | JSON type | Required | Meaning |
|---|---|---:|---|
| `txId` | string | Yes | Fabric transaction ID |
| `timestamp` | string | Yes | History record timestamp formatted as RFC3339 UTC |
| `isDelete` | boolean | Yes | Whether this history entry represents deletion |
| `value` | object or `null` | Yes | Raw historical `Engine` JSON value; `null` for a deletion entry |

## 4. Transaction input JSON schemas

These are client-supplied input shapes. Chaincode-managed fields such as MSP IDs, caller identity, timestamps, transaction IDs, and workflow status must not be accepted from the client.

### 4.1 RegisterEngineInput — `POST /engines`

The current Go input model fields are:

```json
{
  "engineId": "ENGINE-001",
  "manufacturer": "CFM International",
  "model": "LEAP-1A",
  "serialNumber": "SN-001",
  "aircraftMsn": "MSN12345",
  "aircraftRegistration": "CN-ABC",
  "manufactureDate": "2024-05-15",
  "totalFlightMinutes": 12000,
  "totalFlightCycles": 4500,
  "operationalStatus": "SERVICEABLE",
  "location": "Casablanca",
  "statusReason": "",
  "statusEvidenceHash": ""
}
```

Required: `engineId`, `manufacturer`, `model`, `serialNumber`, `manufactureDate`, `totalFlightMinutes`, `totalFlightCycles`, `operationalStatus`.  
Optional: `aircraftMsn` and `aircraftRegistration` (must be supplied together), `location`, `statusReason`, `statusEvidenceHash`.  
Rules: initial operational status cannot be `RETIRED`; numeric values cannot be negative; manufacture date is `YYYY-MM-DD` and cannot be in the future; status reason is required for `UNSERVICEABLE`; evidence hash, when supplied, must be a 64-character hexadecimal SHA-256 digest.

### 4.2 RequestMaintenanceInput — `POST /engines/:id/maintenance/request`

The planned Go input model includes `engineId`, although the REST route already supplies it. A command to add this struct was provided immediately before this contract review, but its presence and local compile result have not yet been confirmed by terminal output. The backend must inject the route ID when serializing the object.

```json
{
  "requestId": "REQ-2026-001",
  "engineId": "ENGINE-001",
  "reason": "Scheduled inspection and oil system check",
  "workScope": ["Inspect oil system", "Inspect fan blades"],
  "priority": "NORMAL",
  "supportingEvidenceHashes": []
}
```

Required: `requestId`, `engineId` (in the serialized chaincode input), `reason`, non-empty `workScope`, `priority`.  
Optional: `supportingEvidenceHashes` (empty array allowed).  
Priority values: `NORMAL`, `HIGH`, `AOG`. Org1 and chaincode supply caller/provider MSPs, caller identity, initial request status and timestamps.

### 4.3 RecordMaintenanceInput — `POST /engines/:id/maintenance`

This input struct has not yet been added to Go. The following field names are proposed to match the persisted `MaintenanceRecord` JSON tags. The backend injects `engineId` from the route.

```json
{
  "recordId": "REC-2026-001",
  "requestId": "REQ-2026-001",
  "engineId": "ENGINE-001",
  "technicianReference": "TECH-042",
  "workOrderReference": "WO-2026-001",
  "maintenanceType": "SCHEDULED_INSPECTION",
  "findings": "Oil filter contamination observed",
  "actionsPerformed": "Filter replaced and system inspected",
  "partsReplaced": [
    {
      "partNumber": "FILTER-001",
      "removedSerialNumber": "OLD-001",
      "installedSerialNumber": "NEW-001"
    }
  ],
  "flightMinutesAtMaintenance": 12000,
  "flightCyclesAtMaintenance": 4500,
  "outcome": "SERVICEABLE",
  "workCompletedAt": "2026-11-27T10:30:00Z",
  "evidenceHashes": [],
  "regulatoryReferences": ["AMM 79-00-00"]
}
```

Required: `recordId`, `requestId`, `engineId` (in serialized chaincode input), `technicianReference`, `workOrderReference`, `maintenanceType`, `findings`, `actionsPerformed`, both flight metrics, `outcome`, `workCompletedAt`.  
Optional: `partsReplaced`, `evidenceHashes`, `regulatoryReferences` (empty arrays allowed).  
Rules: caller must be Org2; request must be the engine's active request; Org2 must have custody; request must be in progress; flight metrics cannot be lower than the current engine totals; outcome must be `SERVICEABLE` or `UNSERVICEABLE`. `workCompletedAt` must not be later than the Fabric transaction timestamp. The chaincode sets provider, recorded time, caller identity and transaction ID.

### 4.4 UpdateEngineStatus — `PATCH /engines/:id/status`

Baseline body matching the previously agreed chaincode signature:

```json
{
  "newStatus": "UNSERVICEABLE",
  "reason": "Oil pressure outside approved operating range",
  "evidenceHash": ""
}
```

Required: `newStatus`, `reason`.  
Optional: `evidenceHash` (if supplied, valid SHA-256). The backend passes four strings after `ctx`: route `engineId`, `newStatus`, `reason`, `evidenceHash`.

**Important unresolved point:** the agreed signature has no `statusType` argument. A previous suggestion to add `statusType` (`OPERATIONAL` / `MAINTENANCE`) would change the agreed signature and is not adopted in this draft. Recommended compatibility approach: infer the target field from the status enum itself. Operational values are `SERVICEABLE`, `UNSERVICEABLE`, `RETIRED`; workflow progress values are `IN_PROGRESS`, `AWAITING_PARTS`. `REQUESTED`, `AWAITING_MAINTENANCE_START`, and `COMPLETED` are set only by their dedicated transactions. Both teammates must approve this before implementation.

### 4.5 TransferEngine — `POST /engines/:id/transfer`

```json
{
  "targetMsp": "Org2MSP",
  "referenceId": "REQ-2026-001"
}
```

Required: `targetMsp`, `referenceId`. The backend passes three individual strings after `ctx`: route `engineId`, `targetMsp`, `referenceId`. The valid target and reference depend on direction; see the custody rules below.

## 5. REST API endpoint contract

### Common REST response envelope (proposed)

Success:

```json
{
  "data": {}
}
```

For list operations, `data` is an array. For single-record operations, `data` is an object. Chaincode returns JSON bytes; the backend decodes UTF-8 and parses JSON before returning it.

Error:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "manufactureDate must use YYYY-MM-DD format"
  }
}
```

The precise error-code mapping is proposed in Section 8 and requires agreement. This envelope is not implemented in the current backend skeleton.

### 5.1 `POST /engines` — RegisterEngine

**Caller:** Org1. **Gateway:** `submitTransaction('RegisterEngine', JSON.stringify(body))`. **Success:** HTTP `201`.

Request: use the `RegisterEngineInput` example in Section 4.1.

Response example:

```json
{
  "data": {
    "docType": "ENGINE",
    "engineId": "ENGINE-001",
    "manufacturer": "CFM International",
    "model": "LEAP-1A",
    "serialNumber": "SN-001",
    "aircraftMsn": "MSN12345",
    "aircraftRegistration": "CN-ABC",
    "manufactureDate": "2024-05-15",
    "totalFlightMinutes": 12000,
    "totalFlightCycles": 4500,
    "operatorMsp": "Org1MSP",
    "custodianMsp": "Org1MSP",
    "operationalStatus": "SERVICEABLE",
    "maintenanceStatus": "NONE",
    "activeMaintenanceRequestId": "",
    "lastMaintenanceRequestId": "",
    "lastMaintenanceRecordId": "",
    "location": "Casablanca",
    "statusReason": "",
    "statusEvidenceHash": "",
    "createdAt": "2026-11-27T10:00:00Z",
    "updatedAt": "2026-11-27T10:00:00Z",
    "createdBy": "<Fabric client identity ID>",
    "updatedBy": "<Fabric client identity ID>"
  }
}
```

### 5.2 `GET /engines` — GetAllEngines

**Caller:** Org1 or Org2. **Gateway:** `evaluateTransaction('GetAllEngines')`. **Success:** HTTP `200`.

Request: no body.

Response example:

```json
{
  "data": [
    {
      "docType": "ENGINE",
      "engineId": "ENGINE-001",
      "manufacturer": "CFM International",
      "model": "LEAP-1A",
      "serialNumber": "SN-001",
      "aircraftMsn": "MSN12345",
      "aircraftRegistration": "CN-ABC",
      "manufactureDate": "2024-05-15",
      "totalFlightMinutes": 12000,
      "totalFlightCycles": 4500,
      "operatorMsp": "Org1MSP",
      "custodianMsp": "Org1MSP",
      "operationalStatus": "SERVICEABLE",
      "maintenanceStatus": "NONE",
      "activeMaintenanceRequestId": "",
      "lastMaintenanceRequestId": "",
      "lastMaintenanceRecordId": "",
      "location": "Casablanca",
      "statusReason": "",
      "statusEvidenceHash": "",
      "createdAt": "2026-11-27T10:00:00Z",
      "updatedAt": "2026-11-27T10:00:00Z",
      "createdBy": "<Fabric client identity ID>",
      "updatedBy": "<Fabric client identity ID>"
    }
  ]
}
```

An empty ledger should return `{"data": []}`, not `null`.

### 5.3 `GET /engines/:id` — ReadEngine

**Caller:** Org1 or Org2. **Gateway:** `evaluateTransaction('ReadEngine', engineId)`. **Success:** HTTP `200`.

Request: no body. Example path: `/engines/ENGINE-001`.

Response: same `Engine` object shape as Section 5.1, inside `data`.

### 5.4 `POST /engines/:id/maintenance/request` — RequestMaintenance

**Caller:** Org1. **Gateway:** `submitTransaction('RequestMaintenance', JSON.stringify(input))`. **Success:** HTTP `201`.

Request example: Section 4.2. Backend takes `engineId` from the route and inserts it into the serialized input.

Response example:

```json
{
  "data": {
    "docType": "MAINTENANCE_REQUEST",
    "requestId": "REQ-2026-001",
    "engineId": "ENGINE-001",
    "requestedByMsp": "Org1MSP",
    "requestedBy": "<Fabric client identity ID>",
    "assignedToMsp": "Org2MSP",
    "reason": "Scheduled inspection and oil system check",
    "workScope": ["Inspect oil system", "Inspect fan blades"],
    "priority": "NORMAL",
    "supportingEvidenceHashes": [],
    "status": "REQUESTED",
    "requestedAt": "2026-11-27T10:10:00Z",
    "updatedAt": "2026-11-27T10:10:00Z",
    "completedAt": ""
  }
}
```

### 5.5 `POST /engines/:id/maintenance` — RecordMaintenance

**Caller:** Org2. **Gateway:** `submitTransaction('RecordMaintenance', JSON.stringify(input))`. **Success:** HTTP `201`.

Request example: Section 4.3. Backend inserts route `engineId` into the serialized input.

Response example:

```json
{
  "data": {
    "docType": "MAINTENANCE_RECORD",
    "recordId": "REC-2026-001",
    "requestId": "REQ-2026-001",
    "engineId": "ENGINE-001",
    "providerMsp": "Org2MSP",
    "technicianReference": "TECH-042",
    "workOrderReference": "WO-2026-001",
    "maintenanceType": "SCHEDULED_INSPECTION",
    "findings": "Oil filter contamination observed",
    "actionsPerformed": "Filter replaced and system inspected",
    "partsReplaced": [
      {
        "partNumber": "FILTER-001",
        "removedSerialNumber": "OLD-001",
        "installedSerialNumber": "NEW-001"
      }
    ],
    "flightMinutesAtMaintenance": 12000,
    "flightCyclesAtMaintenance": 4500,
    "outcome": "SERVICEABLE",
    "workCompletedAt": "2026-11-27T10:30:00Z",
    "evidenceHashes": [],
    "regulatoryReferences": ["AMM 79-00-00"],
    "recordedAt": "2026-11-27T10:45:00Z",
    "recordedBy": "<Fabric client identity ID>",
    "transactionId": "<Fabric transaction ID>"
  }
}
```

### 5.6 `PATCH /engines/:id/status` — UpdateEngineStatus

**Caller:** conditional Org1 or Org2. **Gateway:** `submitTransaction('UpdateEngineStatus', engineId, newStatus, reason, evidenceHash)`. **Success:** HTTP `200`.

Request example: Section 4.4. Response: updated `Engine` object inside `data`.

### 5.7 `POST /engines/:id/transfer` — TransferEngine

**Caller:** conditional Org1 or Org2. **Gateway:** `submitTransaction('TransferEngine', engineId, targetMsp, referenceId)`. **Success:** HTTP `201`.

Request example: Section 4.5.

Response example for Org1-to-Org2 transfer:

```json
{
  "data": {
    "docType": "CUSTODY_TRANSFER",
    "transferId": "<Fabric transaction ID>",
    "engineId": "ENGINE-001",
    "fromMsp": "Org1MSP",
    "toMsp": "Org2MSP",
    "referenceId": "REQ-2026-001",
    "transferredBy": "<Fabric client identity ID>",
    "transferredAt": "2026-11-27T10:20:00Z",
    "transactionId": "<Fabric transaction ID>"
  }
}
```

### 5.8 `GET /engines/:id/history` — GetEngineHistory

**Caller:** Org1 or Org2. **Gateway:** `evaluateTransaction('GetEngineHistory', engineId)`. **Success:** HTTP `200`.

Request: no body.

Response example:

```json
{
  "data": [
    {
      "txId": "<Fabric transaction ID>",
      "timestamp": "2026-11-27T10:00:00Z",
      "isDelete": false,
      "value": {
        "docType": "ENGINE",
        "engineId": "ENGINE-001",
        "manufacturer": "CFM International",
        "model": "LEAP-1A",
        "serialNumber": "SN-001"
      }
    }
  ]
}
```

The actual `value` contains the full historical serialized `Engine` object, not merely the abbreviated example above. Fabric history is expected newest-to-oldest. A deleted key has `isDelete: true` and `value: null`.

### 5.9 `GET /engines/:id/maintenance` — GetMaintenanceHistory

**Caller:** Org1 or Org2. **Gateway:** `evaluateTransaction('GetMaintenanceHistory', engineId)`. **Success:** HTTP `200`.

Request: no body.

Response example:

```json
{
  "data": [
    {
      "docType": "MAINTENANCE_RECORD",
      "recordId": "REC-2026-001",
      "requestId": "REQ-2026-001",
      "engineId": "ENGINE-001",
      "providerMsp": "Org2MSP",
      "technicianReference": "TECH-042",
      "workOrderReference": "WO-2026-001",
      "maintenanceType": "SCHEDULED_INSPECTION",
      "findings": "Oil filter contamination observed",
      "actionsPerformed": "Filter replaced and system inspected",
      "partsReplaced": [],
      "flightMinutesAtMaintenance": 12000,
      "flightCyclesAtMaintenance": 4500,
      "outcome": "SERVICEABLE",
      "workCompletedAt": "2026-11-27T10:30:00Z",
      "evidenceHashes": [],
      "regulatoryReferences": ["AMM 79-00-00"],
      "recordedAt": "2026-11-27T10:45:00Z",
      "recordedBy": "<Fabric client identity ID>",
      "transactionId": "<Fabric transaction ID>"
    }
  ]
}
```

Recommended ordering: oldest-to-newest by `recordedAt`, with `recordId` as a stable tie-breaker. The implementation must explicitly sort because the current index is keyed by engine ID and record ID, not timestamp.

## 6. Maintenance and custody state transition matrix

This is the proposed workflow consistent with the current status constants and original project design. Both members must approve it before the corresponding transactions are implemented.

### 6.1 MaintenanceStatus transitions

| Current status | Next status | Triggering function | Caller / preconditions |
|---|---|---|---|
| `NONE` | `REQUESTED` | `RequestMaintenance` | Org1; engine custodian is Org1; engine not retired; no active request |
| `COMPLETED` | `REQUESTED` | `RequestMaintenance` | Org1; engine custodian is Org1; engine not retired; no active request |
| `REQUESTED` | `AWAITING_MAINTENANCE_START` | `TransferEngine` | Org1 transfers custody to Org2 using the active request ID |
| `AWAITING_MAINTENANCE_START` | `IN_PROGRESS` | `UpdateEngineStatus` | Org2 has custody and active request |
| `IN_PROGRESS` | `AWAITING_PARTS` | `UpdateEngineStatus` | Org2 has custody and active request |
| `AWAITING_PARTS` | `IN_PROGRESS` | `UpdateEngineStatus` | Org2 has custody and active request; work resumes |
| `IN_PROGRESS` | `COMPLETED` | `RecordMaintenance` | Org2 has custody; record matches active request; valid outcome and metrics |
| `AWAITING_PARTS` | `COMPLETED` | Not permitted in this draft | Work must resume (`IN_PROGRESS`) before completion is recorded |

`RequestMaintenance` sets the request status to `REQUESTED`. Moving the engine to `IN_PROGRESS` also moves the request status to `IN_PROGRESS`. `AWAITING_PARTS` does not complete the request. `RecordMaintenance` sets the request to `COMPLETED`, fills `completedAt`, clears the engine's active request ID, and sets its maintenance status to `COMPLETED`.

### 6.2 Custody transitions

| From | To | Function | Required reference | Preconditions |
|---|---|---|---|---|
| `Org1MSP` | `Org2MSP` | `TransferEngine` | Active `MaintenanceRequest.requestId` | Caller Org1; engine custodian is Org1; request belongs to engine, assigned to Org2, and status is `REQUESTED` |
| `Org2MSP` | `Org1MSP` | `TransferEngine` | Completed `MaintenanceRecord.recordId` | Caller Org2; engine custodian is Org2; referenced record belongs to engine and its request is completed; maintenance status is `COMPLETED` |

Custody means physical possession/responsibility, not legal ownership. `operatorMsp` remains `Org1MSP` through both transfers.

### 6.3 OperationalStatus transitions

| Current | Next | Function | Rule |
|---|---|---|---|
| `SERVICEABLE` | `UNSERVICEABLE` | `UpdateEngineStatus` | Authorized current custodian; non-empty reason; evidence hash if provided |
| `UNSERVICEABLE` | `SERVICEABLE` | `RecordMaintenance` only | Only a completed maintenance record with outcome `SERVICEABLE` may restore serviceability |
| `SERVICEABLE` or `UNSERVICEABLE` | `RETIRED` | `UpdateEngineStatus` | Org1 only; custody with Org1; no active maintenance request |
| `RETIRED` | Any other status | Not permitted | Retired is terminal |

A maintenance record with outcome `UNSERVICEABLE` completes the work request but leaves the engine operationally unserviceable. Custody may then return to Org1 after the completed record is committed.

### 6.4 Request and record invariants

- At most one active maintenance request per engine.
- A request must reference an existing, non-retired engine.
- The provider is assigned by chaincode to `Org2MSP`; the client cannot choose another provider.
- A record must reference the engine's current active request and the correct provider organization.
- Flight minutes and flight cycles cannot decrease from the engine's current totals.
- Maintenance records are append-only. Corrections should be new records or explicit correction records, not overwrites.
- `workCompletedAt` is a claimed work-completion time; `recordedAt` is the Fabric transaction timestamp. Neither by itself proves the physical work occurred when claimed.

## 7. Authorization and endorsement

### 7.1 Client MSP authorization

| Operation | Org1 client | Org2 client |
|---|---|---|
| RegisterEngine | Allow | Deny |
| ReadEngine | Allow | Allow |
| GetAllEngines | Allow | Allow |
| RequestMaintenance | Allow | Deny |
| RecordMaintenance | Deny | Allow |
| UpdateEngineStatus | Conditional | Conditional |
| TransferEngine | Conditional | Conditional |
| GetEngineHistory | Allow | Allow |
| GetMaintenanceHistory | Allow | Allow |

The API backend must select a Fabric Gateway identity associated with the authenticated organization. A request body field must never be allowed to select or spoof the caller MSP.

### 7.2 Endorsement

The proposed chaincode policy `AND('Org1MSP.peer','Org2MSP.peer')` requires both organizations' peers to endorse state-changing transactions, regardless of which organization's client submits them. MSP authorization and endorsement are independent checks.

Read-only `evaluateTransaction` calls are evaluated by a peer and are not sent to the ordering service. State-changing `submitTransaction` calls are endorsed, submitted to the orderer and committed; the backend must wait for commit status before returning a success response.

## 8. Validation and error contract

### 8.1 Shared validation rules

- IDs: 1–64 characters; begin with a letter or digit; then letters, digits, `.`, `_`, `-` only. IDs are normalized to uppercase where applicable.
- Required strings: trim surrounding whitespace; reject empty strings; enforce a field-specific maximum length.
- Enum values: exact uppercase values from the allowed enum set.
- Flight times and cycles: non-negative integers and monotonic across maintenance records.
- SHA-256: exactly 64 hexadecimal characters. Hashes identify content; they do not establish evidence authenticity.
- `manufactureDate`: `YYYY-MM-DD`, not in the future relative to the transaction timestamp.
- Event timestamps: RFC3339 / RFC3339Nano with timezone. `workCompletedAt` cannot be later than the transaction timestamp.
- Unknown JSON properties are rejected for complex input JSON.
- Client-submitted MSPs, caller identities, transaction IDs and ledger timestamps are rejected or ignored; chaincode generates them from transaction context.
- All composite-key attributes must be valid UTF-8 and must not contain Fabric's reserved null separator.

### 8.2 Proposed HTTP error mapping

| HTTP status | Error code | Typical cause |
|---:|---|---|
| 400 | `VALIDATION_ERROR` | Missing/invalid field, malformed JSON, invalid enum or hash |
| 401 | `UNAUTHENTICATED` | No valid frontend/backend session or token |
| 403 | `FORBIDDEN` | Authenticated caller is not allowed to perform the operation |
| 404 | `NOT_FOUND` | Engine, request or record does not exist |
| 409 | `CONFLICT` | Duplicate ID/serial, active request already exists, invalid state transition or custody conflict |
| 502 | `FABRIC_UNAVAILABLE` | Gateway, peer, orderer or commit-status communication failure |
| 500 | `INTERNAL_ERROR` | Unexpected backend or chaincode failure |

The stable REST shape should be:

```json
{
  "error": {
    "code": "CONFLICT",
    "message": "engine ENGINE-001 already has an active maintenance request"
  }
}
```

**Implementation gap:** current Go methods generally return ordinary Go errors with human-readable messages, not typed error codes. The backend should not depend on fragile message substring matching. Both members must choose whether to introduce stable chaincode error prefixes (for example `[CONFLICT] ...`) or a structured error convention before the backend error mapper is finalized.

## 9. Engine history and maintenance history implementation requirements

### Engine history

- Query the primary composite key for the engine (`ENGINE` + `engineId`) using `GetHistoryForKey`.
- Map each Fabric history result to `EngineHistoryEntry`: `txId`, `timestamp`, `isDelete`, `value`.
- Preserve the full raw historical Engine JSON in `value`; use JSON `null` for deletion entries.
- Fabric returns history newest-to-oldest.
- `GetHistoryForKey` requires `core.ledger.history.enableHistoryDatabase=true` on the peer. Verify this setting on both Org1 and Org2 peers before integration testing.
- This is a read-only function. Fabric's history query is not re-executed for phantom-read detection, so do not use it inside state-changing operations.

### Maintenance history

- Query the `MAINTENANCE_RECORD_BY_ENGINE` composite-key prefix with the engine ID.
- Resolve each index entry to its primary `MAINTENANCE_RECORD` state, then return `[]*MaintenanceRecord`.
- Sort explicitly by `recordedAt` ascending, then `recordId`, to provide stable oldest-to-newest chronology.
- Return `[]` when there are no records, not `null`.

## 10. Node.js Fabric Gateway connection requirements

The Node backend uses `@hyperledger/fabric-gateway` and `@grpc/grpc-js`. For each organization, the backend must establish a Gateway session with that organization's **client identity**:

1. Create a TLS gRPC client connection to a Gateway-enabled peer endpoint.
2. Trust the peer TLS root CA certificate.
3. Provide the client's X.509 signing certificate and private-key signer.
4. Set the identity MSP ID to exactly `Org1MSP` or `Org2MSP` as appropriate.
5. Connect with the Fabric Gateway Node API (`connect`), then select `getNetwork('mychannel')` and `getContract('aeroengine')`.
6. Use `evaluateTransaction` for the five query operations and `submitTransaction` for the four write operations as listed in Section 2.
7. Decode returned `Uint8Array` values as UTF-8 JSON.
8. Wait for successful commit status before reporting a write as successful.

### Test-network endpoints

When the backend runs in the same WSL environment as the test network, the known peer endpoints are:

| Org | Peer endpoint | TLS server name |
|---|---|---|
| Org1 | `localhost:7051` | `peer0.org1.example.com` |
| Org2 | `localhost:9051` | `peer0.org2.example.com` |

The exact endpoint address, TLS server-name override and CA file path must be adjusted if the backend runs in Windows directly or on another machine. The REST frontend's network location does not change the backend's Fabric connection; only the backend host needs Fabric network access.

### Identity handling

- Use a separate non-admin application identity for each MSP. Test-network `User1` identities may be used for a local demo if present and appropriate; do not use `Admin` identities as application identities.
- Keep identity certificates, private keys and TLS material on the backend host. The Streamlit frontend and teammate must never receive private keys.
- Do not put keys, certificates with private material, wallets, `.env` files or generated identity directories in Git.
- Authenticate frontend users at the backend and map their authenticated account/session to an organization identity. Do not trust an arbitrary `mspId` supplied by the HTTP caller.
- Reuse Gateway/gRPC connections safely; close them during controlled application shutdown.

The current backend skeleton already declares `@hyperledger/fabric-gateway`, `@grpc/grpc-js` and `dotenv`, but does not yet establish a Gateway session or expose any of the nine engine routes.

## 11. Unresolved decisions requiring both members' approval

These are intentionally not silently settled by this draft:

1. **UpdateEngineStatus semantics:** retain the agreed four-string signature and infer whether `newStatus` targets the operational or maintenance status by the enum value (recommended for compatibility), or approve adding an explicit `statusType` argument. The latter changes the agreed function signature and backend call contract.
2. **Request ID and record ID generation:** the current design expects Org1 to supply `requestId` and Org2 to supply `recordId`. Confirm this, or choose chaincode-generated IDs. `transferId` is recommended to use the Fabric transaction ID.
3. **Evidence requirements:** decide whether maintenance evidence hashes are optional or mandatory for particular priorities/outcomes and whether an unserviceable status requires an evidence hash in addition to a reason.
4. **Status permissions:** confirm whether Org1 may mark an engine unserviceable only while it has custody; the recommended rule is yes. Confirm that Org2 may mark an engine unserviceable only while it has custody.
5. **Maintenance completion:** confirm that a record can be created only from `IN_PROGRESS`, and that an `AWAITING_PARTS` engine must return to `IN_PROGRESS` before completion.
6. **History database:** verify `core.ledger.history.enableHistoryDatabase=true` on both peers.
7. **API error codes:** approve the HTTP/error mapping in Section 8 and choose a stable chaincode-to-backend error convention.
8. **REST response envelope and HTTP statuses:** approve `{ "data": ... }` / `{ "error": ... }`, and the proposed 201/200 status codes.
9. **Backend authentication:** choose how the backend authenticates Streamlit users and maps a user to Org1 or Org2. Do not accept organization identity directly from an untrusted request body.
10. **Pagination:** `GetAllEngines` and the initial maintenance-history query are bounded by peer query limits. Decide whether pagination is required for the assessed demo or can be deferred.
11. **Work completion timestamp:** confirm that clients provide `workCompletedAt` and the chaincode rejects future times, while separately setting `recordedAt` from the Fabric transaction timestamp.

## 12. Current implementation status (as of this draft)

According to the latest local work shared in the development chat:

- Verified locally through terminal output: Go module and dependencies; domain structs including `Engine`, `MaintenanceRequest`, `MaintenanceRecord`, `CustodyTransferRecord`, `PartReplacement`, and `EngineHistoryEntry`; `RegisterEngineInput`; MSP authorization helpers; input validators; storage helpers; `RegisterEngine`; `ReadEngine`; and `GetAllEngines`.
- Unit tests for validation, storage, registration, and read operations have passed using local mock implementations.
- `RequestMaintenanceInput` was proposed in a command immediately before this contract review; whether that command was run and compiled is not yet confirmed.
- Not yet implemented: `RequestMaintenance`, `RecordMaintenance`, `UpdateEngineStatus`, `TransferEngine`, `GetEngineHistory`, `GetMaintenanceHistory`, chaincode entry point, deployment and live Gateway integration.
- Unit tests using mock state do not prove real Fabric endorsement, identity authorization, MVCC behavior, peer query limits or Gateway connectivity. These require integration tests on the existing two-organization network.

**Repository visibility note:** at the time this draft was prepared, remote `dev-blockchain` was at commit `f208cd8` and did not yet contain the local `chaincode/` directory. The local Go work must be staged, reviewed for secrets/generated files, committed and pushed before another collaborator or their GitHub-connected assistant can inspect it remotely.

## 13. Reference documentation

- [Hyperledger Fabric Gateway Node.js API](https://hyperledger.github.io/fabric-gateway/main/api/node/)
- [Gateway `connect()` API](https://hyperledger.github.io/fabric-gateway/main/api/node/functions/connect.html)
- [Gateway Contract API — evaluate and submit transactions](https://hyperledger.github.io/fabric-gateway/main/api/node/interfaces/Contract.html)
- [Fabric chaincode shim interfaces](https://github.com/hyperledger/fabric-chaincode-go/blob/main/shim/interfaces.go)

---

**Approval checklist**

- [ ] User / blockchain developer reviewed function signatures, data fields and transition rules.
- [ ] Teammate / application developer reviewed REST routes, request bodies and response envelopes.
- [ ] Both members approved the unresolved decisions in Section 11.
- [ ] The approved version is committed on `dev-blockchain` and shared with the application branch.
