# AeroEngine-Blockchain — Fact Check & Project Handoff

Last updated: 2026-11-27  
Purpose: preserve verified project facts, current implementation state, decisions, and next steps when continuing in another ChatGPT chat.

## 1. Project overview

**Project:** Aircraft Engine Maintenance and Traceability Using Blockchain  
**Repository:** `Yassine-mounabih/AeroEngine-Blockchain` (private)  
**Goal:** build an original distributed application using Hyperledger Fabric to track aircraft engines, maintenance requests, maintenance interventions, and custody transfers.

This must go beyond the Fabric `asset-transfer` sample. The final project must include custom chaincode, a client application that actually invokes it, and a demonstration showing shared ledger state from both organization contexts.

## 2. Verified environment and Fabric network

- Host: Windows + WSL2 + Ubuntu 24.04 + Docker Desktop.
- Fabric version: **2.5.16**.
- Fabric samples: `~/fabric/fabric-samples`.
- Project clone: `~/AeroEngine-Blockchain`.
- Fabric test network was started from `~/fabric/fabric-samples/test-network` using:
  ```bash
  ./network.sh up createChannel
  ```
- Channel: `mychannel`.
- Orderer: `orderer.example.com`, localhost port `7050`.
- Org1 peer: `peer0.org1.example.com`, Org1MSP, localhost port `7051`.
- Org2 peer: `peer0.org2.example.com`, Org2MSP, localhost port `9051`.
- The shared channel is a Raft-based channel with both organizations.
- Fabric CLI environment in WSL:
  ```bash
  export PATH="$HOME/fabric/fabric-samples/bin:$PATH"
  export FABRIC_CFG_PATH="$HOME/fabric/fabric-samples/config"
  ```
- From the test-network directory:
  ```bash
  source scripts/envVar.sh
  setGlobals 1   # Org1
  setGlobals 2   # Org2
  ```

**Do not tear down or recreate the existing Fabric network.** Do not remove unrelated Docker containers or data. Other containers previously observed (`nostalgic_hamilton`, `manticlone-app-1`, `manticlone-db-1`) are unrelated and must be left untouched.

## 3. Basic Fabric exercise already completed

The sample Go chaincode `asset-transfer-basic` was deployed to `mychannel` under chaincode name `basic`.

- Chaincode version: `1.0`, sequence `1`.
- Both Org1 and Org2 installed and approved the definition.
- Committed endorsement policy:
  ```text
  AND('Org1MSP.peer','Org2MSP.peer')
  ```
- `InitLedger` was invoked.
- `asset1` was queried successfully from both Org1 and Org2.
- `asset6` was transferred from Michel to Christopher.
- The invocation was valid, and Org2 subsequently queried the updated owner.
- This verified that both organizations see the same channel ledger state.

This was only a Fabric proof-of-concept. It is **not** the final application and does not satisfy the custom-business-logic requirement by itself. Keep `basic` deployed; it can coexist with the custom chaincode.

## 4. Professor's project requirements

The professor's requirements PDF is stored in the ChatGPT Library at:

`/AeroEngine-Blockchain/Projet_applicatif.pdf`

Key minimum requirements extracted from pages 9–10:

1. Working Fabric network with at least two organizations, a channel, and peers.
2. A tailored data model and project-specific business rules implemented in custom chaincode.
3. Several relevant business operations, including create, consult, update, or transfer.
4. A client application (web, mobile, desktop, or API plus demo client) that genuinely interacts with the chaincode and ledger.
5. Demonstration of at least one transaction, its result, and consultation from two organization contexts.

Expected deliverables include source code, network/configuration, chaincode, client application, dependencies/scripts, a design document, test scenarios (including cross-organization checks), and a 10-minute demo.

## 5. Shared repository and branches

Private repository: `Yassine-mounabih/AeroEngine-Blockchain`

- `main`: stable integrated branch.
- `dev-blockchain`: user's branch, Fabric/network/Go chaincode.
- `dev-application`: teammate's branch, Node.js backend and Streamlit frontend.

User's GitHub account: `KhalilAbboud`. GitHub CLI authentication and `gh auth setup-git` were configured in WSL. User has WRITE permission.

At last known remote inspection:
- `dev-blockchain`: `05e8f446387c4331d452eafb7c934790c633684f`
- `dev-application`: `26ee9ebcbac521354dada7b12d11dc90457b0397`
- `main`: `05e8f446387c4331d452eafb7c934790c633684f`

A recent `git pull --ff-only origin dev-blockchain` failed due to a transient WSL DNS failure (`Could not resolve host: github.com`). Do not assume this is an authentication problem. Retry only when network/DNS is working and needed. Avoid destructive Git commands. The user prefers to run commands locally and share output; do not push or commit on their behalf unless explicitly asked.

## 6. Fixed project naming and application configuration

Keep these names consistent across chaincode, backend, frontend, docs, and deployment:

| Setting | Value |
|---|---|
| Project | `AeroEngine-Blockchain` |
| Channel | `mychannel` |
| Custom chaincode | `aeroengine` |
| Org1 MSP | `Org1MSP` |
| Org2 MSP | `Org2MSP` |
| Org1 role | Airline company |
| Org2 role | Maintenance company |
| Backend | Node.js / JavaScript, port `3000` |
| Frontend | Python / Streamlit, port `8502` |
| Chaincode | Go |

REST API agreed with teammate:

| HTTP route | Chaincode operation |
|---|---|
| `POST /engines` | `RegisterEngine` |
| `GET /engines` | `GetAllEngines` |
| `GET /engines/:id` | `ReadEngine` |
| `POST /engines/:id/maintenance/request` | `RequestMaintenance` |
| `POST /engines/:id/maintenance` | `RecordMaintenance` |
| `PATCH /engines/:id/status` | `UpdateEngineStatus` |
| `POST /engines/:id/transfer` | `TransferEngine` |
| `GET /engines/:id/history` | `GetEngineHistory` |
| `GET /engines/:id/maintenance` | `GetMaintenanceHistory` |

The backend will use Hyperledger Fabric Gateway. The frontend will call the backend API; it should not connect directly to Fabric.

## 7. Organization responsibilities and security model

- **Org1MSP (airline):** registers engines, requests maintenance, consults engine and maintenance history, initiates transfer to the maintenance provider when a valid maintenance request exists.
- **Org2MSP (maintenance company):** records maintenance work, updates maintenance-related engine condition/status, consults records, and returns custody to the airline after recording completed maintenance.
- Custody transfer represents physical custody, not legal ownership. The airline remains the operator.
- Initial chaincode endorsement policy for the custom chaincode is intended to be:
  ```text
  AND('Org1MSP.peer','Org2MSP.peer')
  ```
  This means both organizations' peers endorse state-changing transactions. It is separate from chaincode authorization, which checks the submitting client's MSP.
- Chaincode MSP checks currently authorize by organization only. They do not distinguish employees or roles within an organization.
- Do not use peer identity/environment variables to determine the transaction submitter. Use the transaction client's identity via Fabric chaincode client identity (`cid`).
- For the final backend, use separate non-admin client identities for Org1 and Org2. Do not use admin identities as application identities. Fine-grained employee roles can later use Fabric CA certificate attributes.
- Never commit wallets, private keys, certificates containing private material, `.env`, or identity files. Keep private identity material local. Do not expose Docker socket or copy private keys to the teammate.

## 8. Domain model and business rules (design draft; refine before finalizing)

Proposed entities:

- `Engine`
- `MaintenanceRequest`
- `PartReplacement`
- `MaintenanceRecord`
- `CustodyTransferRecord`
- `EngineHistoryEntry`

### Engine fields

```text
DocType, EngineID, Manufacturer, Model, SerialNumber,
AircraftMSN, AircraftRegistration, ManufactureDate,
TotalFlightMinutes, TotalFlightCycles,
OperatorMSP, CustodianMSP,
OperationalStatus, MaintenanceStatus,
ActiveMaintenanceRequestID, LastMaintenanceRequestID,
LastMaintenanceRecordID, Location, StatusReason,
CreatedAt, UpdatedAt, CreatedBy, UpdatedBy
```

Operational status is separate from maintenance workflow status:

- Operational: `SERVICEABLE`, `UNSERVICEABLE`, `RETIRED`.
- Maintenance: `NONE`, `REQUESTED`, `AWAITING_MAINTENANCE_START`, `IN_PROGRESS`, `AWAITING_PARTS`, `COMPLETED`.

### MaintenanceRequest

```text
DocType, RequestID, EngineID, RequestedByMSP, RequestedBy, AssignedToMSP,
Reason, WorkScope []string, Priority, SupportingEvidenceHashes []string,
Status, RequestedAt, UpdatedAt, CompletedAt
```

Priority: `NORMAL`, `HIGH`, `AOG`.  
Request status: `REQUESTED`, `IN_PROGRESS`, `COMPLETED`.

### MaintenanceRecord

```text
DocType, RecordID, RequestID, EngineID,
ProviderMSP, TechnicianReference,
WorkOrderReference, MaintenanceType,
Findings, ActionsPerformed,
PartsReplaced []PartReplacement,
FlightMinutesAtMaintenance int64, FlightCyclesAtMaintenance int64,
Outcome (`SERVICEABLE` or `UNSERVICEABLE`),
WorkCompletedAt,
EvidenceHashes []string, RegulatoryReferences []string,
RecordedAt, RecordedBy, TransactionID
```

Maintenance records should be append-only. Corrections should be represented by new records rather than overwriting old records. `WorkCompletedAt` is the submitted claim of when work was completed; `RecordedAt` should come from the Fabric transaction timestamp and does not independently prove when physical work happened.

### CustodyTransferRecord

```text
DocType, TransferID, EngineID, FromMSP, ToMSP,
ReferenceID, TransferredBy, TransferredAt, TransactionID
```

Permitted transfer directions:
- Org1 → Org2 with a valid maintenance request (Org1 submits).
- Org2 → Org1 with a completed maintenance record (Org2 submits).

### History

`EngineHistoryEntry` should capture `TxID`, timestamp, delete flag, and raw value. `GetHistoryForKey` requires peer history database support; verify this setting on both peers before relying on it.

### Important invariants to implement

- Engine IDs and serial numbers must be unique.
- At most one active maintenance request per engine.
- Flight minutes and cycles must never decrease.
- Only permitted organizations can execute each business operation.
- Maintenance and custody state transitions must be validated.
- A maintenance record must reference the correct engine and active request.
- Recording maintenance should complete the request and update engine maintenance status. The record outcome determines operational status (`SERVICEABLE` or `UNSERVICEABLE`).
- After maintenance, custody can be returned to Org1; operational status remains determined by the maintenance outcome.
- Use Fabric transaction timestamps for ledger event times; keep claimed work completion time separate and validate it.
- Store document/photo contents off-chain; store SHA-256 evidence hashes on-chain.
- Define and test a coherent state transition table before implementing all transaction functions.

## 9. Current custom Go chaincode work (verified as of 2026-11-27)

Local working directory:

`~/AeroEngine-Blockchain/chaincode/aeroengine`

Go module:

```text
module github.com/Yassine-mounabih/AeroEngine-Blockchain/chaincode/aeroengine

go 1.25.0
```

Direct dependencies:

```text
github.com/hyperledger/fabric-chaincode-go/v2 v2.0.0
github.com/hyperledger/fabric-contract-api-go/v2 v2.2.0
```

`go mod tidy` completed and downloaded dependencies. `go test ./...` succeeded.

Current source layout:

```text
chaincode/
  aeroengine/
    go.mod
    go.sum
    chaincode/
      models.go
      authorization.go
```

`models.go` was created, formatted, and compiled. It contains the domain structs and status/priority/outcome constants described above. The `MaintenanceRecord` field is named `TechnicianReference`.

`authorization.go` was created and verified by reading the file back with `sed`. The pasted terminal echo initially looked corrupted around the heredoc terminator, but the actual saved file was complete and correctly formatted.

It contains:
- `Org1MSP = "Org1MSP"`
- `Org2MSP = "Org2MSP"`
- `requireMSP(ctx, expectedMSP)` which checks the transaction submitter's MSP and returns its client identity ID.
- `requireOrganization(ctx)` which permits either Org1MSP or Org2MSP and returns caller MSP plus client identity ID.
- Uses:
  ```go
  github.com/hyperledger/fabric-chaincode-go/v2/pkg/cid
  github.com/hyperledger/fabric-contract-api-go/v2/contractapi
  ```

Last verified command from module root:

```bash
go test ./...
```

Output:

```text
? github.com/Yassine-mounabih/AeroEngine-Blockchain/chaincode/aeroengine/chaincode [no test files]
```

This verifies compilation, not behavioral correctness. No chaincode contract entry point, transaction functions, unit tests, or deployment have been implemented yet.

Last `git status --short` from repository root:

```text
?? chaincode/
```

The chaincode project is untracked locally and has not been committed or pushed. Preserve it.

## 10. Immediate next steps

Proceed incrementally, checking terminal output after each step:

1. **Review `models.go` and `authorization.go`** for field naming and consistency. Do not overwrite correct files.
2. Add input validation helpers in `validation.go`: required strings, allowed enum values, numeric non-negative values, timestamps, evidence hash format, and safe IDs. Keep validation separate from transaction methods.
3. Add the Fabric contract/transaction implementation (likely `smartcontract.go` and `contract.go`):
   - `RegisterEngine`
   - `ReadEngine`
   - `GetAllEngines`
   - `RequestMaintenance`
   - `RecordMaintenance`
   - `UpdateEngineStatus`
   - `TransferEngine`
   - `GetEngineHistory`
   - `GetMaintenanceHistory`
4. Before implementing state transitions, define an explicit transition matrix and validate all invariants. Avoid coding ambiguous workflow states.
5. Add composite-key indexes and deterministic queries. Verify history DB availability before using `GetHistoryForKey`.
6. Add unit tests using Fabric chaincode mocks where practical; test authorization, invalid transitions, duplicate IDs/serials, active request constraints, monotonic flight metrics, and cross-organization behavior.
7. Add `main.go` to create and start the contract chaincode.
8. Build and test chaincode locally, then package/install/approve/commit `aeroengine` on `mychannel` with the agreed two-org endorsement policy. Keep the existing `basic` chaincode untouched.
9. Generate/use proper non-admin Org1 and Org2 client identities for backend Gateway connections.
10. Integrate teammate's Node.js backend (port 3000) with Fabric Gateway and implement the agreed REST routes.
11. Integrate Streamlit frontend (port 8502) with the backend; test actual ledger read/write flows.
12. Demonstrate an engine registration, maintenance request, custody transfer, maintenance record, return transfer, and query from both organization contexts.
13. Update README, architecture/design documentation, setup scripts, test evidence, and 10-minute demo plan.
14. Commit and push from the user's local WSL Git checkout after reviewing changes. Do not commit secrets or private identity material.

## 11. Collaboration and working style

- Work in small, verifiable steps.
- Give exact commands and specify the working directory.
- Wait for the user to share command output before moving to the next step.
- Prefer short, direct explanations.
- Do not repeat completed setup steps or recreate the Fabric network.
- Do not assume a command succeeded just because it was provided; verify outputs.
- Distinguish verified implementation from design proposals and future work.
- If continuing in a new chat, use this document as the project handoff and first check the current local Git status and files before modifying anything.
