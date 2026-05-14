# Railway PVC SaaS Reverse Engineering Report

## 1. Executive Summary

This operating model is not a generic billing or accounting workflow. It is a contract-interpretation and bill-normalization system for Indian Railways works contracts, where the commercial truth is spread across:

- tender tabulation and agreement clauses
- schedule-level contract pricing
- e-MB measurements
- running bill statements
- recovery sheets
- PVC index tables
- Excel workbooks with operator-maintained logic

The uploaded sample shows a real railway works contract:

- Tender: `BCT-24-25-252`
- Agreement: `WR/BCT/Civil/2025/0059`
- LOA: `00944450126035`
- LOA date: `2025-03-25`
- Work: `Colaba-Badhwarpark-Repairs to change of officers quarter in connection to new occupation at Badhwar Park Railway officers colony.`
- Contract completion date in agreement: `2026-03-25`
- Tender amount in agreement PDF: about `Rs. 2.56 crore`
- Bid amount in agreement PDF: about `Rs. 1.108 crore`
- LOA amount in agreement PDF: about `Rs. 1.077 crore`

The current operating system is spreadsheet-centric because users trust explicit numbers, visible formulas, and bill-wise tabulation. A successful cloud product should preserve that trust model while fixing current weaknesses:

- hidden formula risk
- weak auditability
- difficult document traceability
- manual index selection
- poor treatment of contract edge cases
- repeated copy-paste from MB to bill to PVC sheet

The workbook demonstrates that PVC is not computed on gross bill value directly. The actual operational engine is:

1. derive bill-wise eligible amount buckets
2. exclude non-eligible categories from the general PVC base
3. split steel and cement into separate componentized calculations
4. apply quarter-average indices against a configured base month
5. aggregate escalation or de-escalation component-wise
6. produce a contractor-facing and submission-ready PVC sheet

The SaaS opportunity is a contract-aware calculation and audit platform with:

- spreadsheet-grade operator control
- configurable tender-specific PVC rules
- bill/MB/recovery traceability
- versioned calculation snapshots
- Excel import/export parity
- approval-ready reports

## 2. Workflow Breakdown

### 2.1 End-to-End Railway Contractor Workflow

1. Tender discovery and bid participation
2. Financial tabulation review
3. Agreement issuance and LOA finalization
4. Contract setup with schedule items, bid discounts, rebate, and PVC applicability
5. Site execution and MB recording
6. Running bill preparation from MB quantities
7. Recovery computation and deductions
8. PVC calculation for eligible bill portions
9. Internal review by contractor/billing engineer
10. Submission to railway
11. Subsequent bill/revision/final bill closure

### 2.2 Observed Operational Dependency Chain

`Tender -> Agreement -> Schedule/BOQ -> MB -> Running Bill -> Recoveries -> PVC Sheet -> Submission`

PVC depends on bill values, but bill values depend on MB execution, and the bill must be normalized before PVC can be applied.

### 2.3 User Personas

1. Contractor principal / management
- wants bill status, cash-flow visibility, PVC receivable visibility
- cares about claim completeness and audit defense

2. Billing engineer / billing operator
- prepares RA bills
- transcribes quantities from MB
- validates cumulative vs since-last-bill quantities
- prepares PVC sheets
- manages Excel logic today

3. Site engineer / measurement engineer
- records or verifies measurements
- manages item-level quantity buildup
- handles carry-forward and cumulative execution

4. Accounts / deductions operator
- tracks security deposit, IT, labour cess, water charges, statutory deductions
- reconciles gross bill vs net payable

5. Contract admin / setup operator
- configures tender details, base month, component weights, indices, exclusions

6. Reviewer / approver
- checks clause compliance, formula correctness, and submission readiness

7. Railway-facing liaison
- needs printable outputs and defensible calculation packs

### 2.4 Workflow Inferred from the Uploaded Files

#### A. Tender / Agreement Setup

From the agreement and tender tabulation:

- Schedule A is DSR-based and bid at `58.58% below`
- Schedule B is NS items and bid at `49% below`
- Overall rebate is `2.75%`
- PVC applicability is present under GCC Clause 46A
- Agreement text explicitly states extra items are outside PVC unless specifically agreed with applicable PVC/base month terms

This implies the setup stage must capture:

- schedule-level pricing logic
- base month
- PVC applicability
- item classes that are separately index-linked
- rebate and rate build-up sequence
- whether extra items are PVC-eligible

#### B. Measurement Book Layer

The MB PDFs show:

- work metadata
- measurement dates
- item-wise measurements
- dimensional buildup
- test-check flags
- quantity brought forward from prior MB
- "Now to pay 100%" style payment status

The MB is the source of quantity truth, but it is not yet the payment truth. Payment may still depend on:

- agreement quantity caps or revisions
- carried-forward quantities
- split payment logic
- schedule classification

#### C. Running Bill Layer

The bill PDFs show item-wise execution fields:

- original agreement quantity
- current agreement quantity
- quantity executed up to last bill
- quantity executed since last bill
- quantity up to date
- amount up to last bill
- amount since last bill
- amount including special condition
- total up to date amount

This confirms the bill engine is cumulative, not isolated per period. The product must preserve both:

- cumulative value
- incremental since-last-bill value

#### D. Recovery Layer

The recovery PDFs show recoveries such as:

- security deposit
- water and cess charges
- income tax deduction
- labour cess

For the sample:

- 1st bill amount: about `Rs. 93.06 lakh`
- 1st bill recoveries: about `Rs. 4.98 lakh`
- 1st net payable: about `Rs. 88.08 lakh`

- 2nd bill amount: about `Rs. 67.37 lakh`
- 2nd bill recoveries: about `Rs. 4.37 lakh`
- 2nd net payable: about `Rs. 63.01 lakh`

Recoveries matter operationally and for final payable amounts, but not every recovery should affect PVC eligibility. This distinction must be explicit in the rules model.

#### E. PVC Workbook Layer

The workbook contains these sheets:

- `Front Page`
- `Index`
- `Second Page`
- `Cement`
- `Steel`
- `10.2`
- `Bill- 1`
- `Bill-2`

This structure reveals the actual business process:

1. capture base and current indices
2. derive category-specific eligible bill values
3. isolate cement amount
4. isolate steel amount by sub-type
5. derive general PVC base `W`
6. apply separate formulas by contract classification
7. roll the total to a summary front page

### 2.5 Repetitive Manual Tasks

- reading agreement clauses and manually configuring them in Excel
- copying bill totals into quarter sheets
- extracting cement-related execution from bill items
- splitting steel quantities into angle/channel/beam/plate/other
- applying carry-forward quantities manually
- fetching and entering published indices month by month
- averaging quarterly indices
- checking whether extra items should be excluded
- reconciling bill totals, recoveries, and PVC base amount
- generating print-ready submission formats

### 2.6 Operational Bottlenecks

- contract interpretation depends on individual operator memory
- formulas are hidden inside spreadsheets
- there is no immutable audit trail of who changed which assumption
- bill revisions are difficult to replay safely
- extra item eligibility is easy to mishandle
- carrying forward partial steel quantities is error-prone
- cumulative and incremental quantities can diverge silently

### 2.7 Why Excel Still Dominates

The current workflow is spreadsheet-native because users need:

- visible arithmetic
- row-wise control
- local overrides
- immediate recalculation
- easy print/export

A successful SaaS product should not replace spreadsheet thinking. It should formalize it.

## 3. Entity Model

### 3.1 Core Business Entities

1. Tenant
- contractor organization / business unit

2. Workspace or project
- logical grouping for a tender or contract

3. Tender
- tender number
- tender tabulation
- advertised value
- schedule structures

4. Agreement / contract
- agreement number
- LOA number/date
- contractor
- contract value
- start/completion dates
- GST mode
- PVC applicability
- base month
- rebate

5. Schedule
- Schedule A / B / C etc.
- type: DSR, NS, extra NS
- bid style
- schedule-level discount or special pricing logic

6. Contract item
- item code
- description
- unit
- original qty
- revised qty
- base rate
- agreement rate
- schedule
- classification tags

7. Measurement book
- MB number
- measurement period
- source PDF
- certification metadata

8. Measurement line
- MB reference
- item code
- location
- dimensional breakup
- measured qty
- cumulative qty
- test-check status
- remarks

9. Running bill
- bill number
- bill date
- linked MB(s)
- schedule totals
- GST
- gross amount
- net amount

10. Bill line
- item code
- qty up to last bill
- qty since last bill
- qty up to date
- amount since last bill
- total up to date
- special-condition amount

11. Recovery
- bill reference
- recovery type
- recovery code
- amount
- eligibility impact on PVC

12. Index series
- labour
- plant and machinery
- fuel
- other materials
- cement
- TMT
- angles
- plates
- other sections

13. Index observation
- month
- published index value
- source reference
- revision flag

14. PVC rule set
- formula template
- classification-specific weights
- averaging method
- exclusions
- rounding
- extra-item policy

15. PVC run
- contract
- bill / quarter
- index snapshot
- rule snapshot
- outputs
- exported files

16. PVC component result
- category
- eligible amount
- base index
- current/average index
- component weight
- calculated value

17. Approval / review action
- stage
- actor
- decision
- notes

18. Document
- uploaded file
- type
- OCR text
- parsed entities
- version

19. Revision snapshot
- immutable snapshot of bill, indices, rules, and outputs

### 3.2 Key Relationships

- Tenant `1..n` Contracts
- Contract `1..n` Schedules
- Schedule `1..n` ContractItems
- Contract `1..n` MBs
- MB `1..n` MeasurementLines
- Contract `1..n` Bills
- Bill `1..n` BillLines
- Bill `1..n` Recoveries
- Contract `1..n` PVC runs
- PVC run `1..n` PVC component results
- Contract `1..n` Index configurations
- Index series `1..n` Index observations
- Contract `1..n` Documents

### 3.3 Lifecycle States

#### Contract
- Draft
- Configured
- Active
- Suspended
- Completed
- Archived

#### MB
- Uploaded
- Parsed
- Reviewed
- Approved
- Locked

#### Bill
- Draft
- Imported
- Reconciled
- Approved internally
- Submitted
- Revised
- Locked

#### PVC Run
- Draft
- Calculated
- Exception flagged
- Approved
- Exported
- Superseded

### 3.4 ERD Recommendation

Use a normalized operational schema plus immutable snapshots:

- normalized tables for current state and searchability
- append-only snapshot tables for calculation reproducibility

Recommended snapshot artifacts:

- `contract_rule_snapshot`
- `bill_snapshot`
- `index_snapshot`
- `pvc_run_snapshot`
- `export_snapshot`

### 3.5 Multi-Tenant Considerations

- row-level tenancy by `tenant_id`
- object storage scoped per tenant and contract
- formula templates can be tenant-specific or platform-default
- approval workflows may vary by organization
- some contractors may want isolated deployment later

## 4. Data Flow Diagrams

### 4.1 Operational Data Flow

`Tender PDF / Agreement PDF -> Contract setup -> Schedule and rule extraction -> MB ingestion -> Bill ingestion -> Recovery ingestion -> Index ingestion -> PVC normalization -> Component-wise calculation -> Review -> Export`

### 4.2 Bill-to-PVC Normalization Flow

`Bill gross amount -> subtract cement bucket -> subtract steel buckets -> subtract technical withheld if applicable -> subtract extra-item bucket if non-eligible -> derive W -> apply 9A/9C/9D style formulas -> aggregate`

### 4.3 Document Parsing Flow

`Upload -> classification -> OCR/text extraction -> parser templates -> human review -> canonical entities -> immutable source link`

### 4.4 Submission Flow

`PVC run -> report generation -> Excel parity export -> PDF print pack -> approval note -> submission record`

## 5. PVC Engine Reverse Engineering

### 5.1 What the Workbook Is Actually Doing

The workbook is not one formula. It is a pipeline.

#### Step 1: Define base month and index table

In `Index`:

- Base month: `Dec-24`
- Base indices for:
  - labour
  - plant and machinery
  - fuel and lubricants
  - other materials
  - cement
  - TMT
  - angles
  - plates
  - other sections

Monthly values are entered and quarter averages are derived.

#### Step 2: Derive the bill-wise eligible amount `W`

In `Second Page`, for 1st bill:

- On-account bill amount: `9305888.90`
- Cement amount: from `Cement!H19`
- Steel angle/channel/beam amount: from `Steel!H11`
- Steel plate amount: from `Steel!H12`
- Other steel amount: from `Steel!H14`
- `W = D - E - G - H - I`

The formula in the workbook is effectively:

`W = OnAccountBill - CementAmount - SteelAnglesAmount - SteelPlateAmount - SteelOtherSectionsAmount - TechnicalRecovery - ExtraItemAmount`

In the current sample, technical recovery and extra-item cells are blank/zero.

#### Step 3: Compute cement amount separately

In `Cement`:

- each bill line has item code, executed qty, unit, consumption factor, derived cement quantity, cement rate, cement amount
- cement amount is `executed quantity * cement consumption factor * derived cement rate`

This is contract-specific cost build-up, not a generic standard formula.

#### Step 4: Split steel amount into component buckets

In `Steel`:

- structural steel under item `10.2` is split into:
  - angle
  - channel
  - beam
  - plate
- `9.48.2` is treated as "Others"
- `10.28` is also treated as another steel-related bucket

This is important: PVC is calculated not simply by item code, but by item-class and material subtype.

#### Step 5: Handle carry-forward quantities

For item `10.2`, measured quantity was higher than first-bill payable quantity.

The sheet computes a paid percentage:

- recorded qty total: `6172.57`
- paid qty in first bill: `5600`
- paid ratio: about `0.9072396101`

Then it prorates the first bill's steel subtypes by that percentage and carries the balance into the next bill:

- first bill remarks: `Qty C/F in 2nd & F Bill`
- second bill remarks: `Qty B/F from 1st R Bill`

This is a critical domain behavior. The system must support:

- recorded quantity
- paid quantity
- carried-forward payable quantity
- bill-to-bill allocation history

#### Step 6: Apply componentized PVC formulas

For `Bill-1`, the workbook uses:

`PVC = Amount * ((QuarterAverageIndex - BaseIndex) / BaseIndex) * ComponentWeight`

Examples:

- general labour on `W`: weight `0.20`
- plant and machinery on `W`: weight `0.30`
- fuel on `W`: weight `0.15`
- other materials on `W`: weight `0.20`
- cement-specific PVC on cement amount: weight `0.85`

For structural steel categories, each steel bucket gets split into:

- labour `0.10`
- steel commodity index `0.50`
- plant and machinery `0.10`
- fuel `0.10`
- other materials `0.05`

The adjustable portion totals `0.85`, implying a residual non-variable fraction of `0.15`.

### 5.2 Important Formula Findings

#### Finding 1: W is a normalized bill value, not a raw bill value

The product must explicitly model `PVC-eligible normalized amount` rather than using gross bill amount.

#### Finding 2: Cement uses a rate build-up before indexing

The cement rate note shows:

- DSR rate basis
- schedule escalation adjustment
- schedule discount / contract percentage
- rebate adjustment

This means a rules engine must support stacked rate transforms before PVC.

#### Finding 3: Steel PVC is subtype-aware

Different steel categories map to different published indices:

- angles
- plates
- other sections
- potentially TMT / rounds

#### Finding 4: Quantity carry-forward is part of the calculation engine

PVC eligibility can depend on payable quantity, not just measured quantity.

#### Finding 5: Extra items are contractually excluded unless expressly allowed

The agreement text under PVC applicability says extra items outside BOQ are excluded unless separately agreed.

But in the sample:

- 2nd bill recovery sheet includes `Schedule C-Extra NS` amount around `Rs. 13.42 lakh`
- `Second Page` extra-item deduction column is blank for 2nd bill
- `W` therefore appears to include extra-item value

This is a high-risk manual/spreadsheet governance issue. The SaaS product should not allow silent inclusion of extra items.

#### Finding 6: The sample workbook appears to contain a quarter-index reference risk

`Bill-2` is labeled `Quarter No. 4`, but the formulas reference `Index!$C$9`, `Index!$D$9`, etc., which correspond to the quarter-2 average row, not the quarter-4 average row (`Index` row 16).

This may be:

- a spreadsheet mistake
- an operator copy-forward issue
- or a domain-specific practice not fully represented in the sheet

The platform must surface such mismatches automatically.

### 5.3 What Should Be Configurable

1. PVC applicability by contract
2. base month
3. index families used
4. averaging method:
- monthly
- quarterly average
- bill-date month
- lagged publication method

5. classification groups:
- general works
- cement supply
- steel fabrication
- TMT
- fuel-sensitive work

6. component weights
7. exclusion rules
8. extra-item treatment
9. railway-supplied materials treatment
10. rate build-up sequence
11. carry-forward rules
12. rounding policy
13. negative PVC policy
14. retro index revision policy

### 5.4 What Should Not Be Hardcoded

- formula weights
- index names
- quarter logic
- extra item inclusion/exclusion
- cement consumption factors
- steel subtype mapping
- bid discount sequencing
- rebate interaction

### 5.5 Recommended Rules Engine Structure

Use a versioned declarative rule system with these layers:

1. Contract rule pack
- base month
- effective dates
- applicability thresholds

2. Eligibility extractor rules
- derive `W`
- derive cement bucket
- derive steel bucket
- derive extra-item exclusion

3. Rate derivation rules
- DSR base
- schedule escalation adjustment
- bid discount
- rebate

4. Index mapping rules
- component -> index series
- monthly/quarter averaging logic

5. Component formula rules
- category-wise weight sets

6. Post-processing rules
- rounding
- negative handling
- display formatting

Store each rule pack as versioned JSON plus generated human-readable documentation.

## 6. SaaS Architecture Proposal

### 6.1 Product Shape

This should start as a workflow-heavy operational SaaS, not a microservices-first platform.

Recommended shape for MVP:

- web app
- API backend
- background workers
- PostgreSQL
- object storage
- rules engine module
- document ingestion module

### 6.2 Frontend Architecture

Recommended:

- `Next.js` with React
- `TypeScript`
- `AG Grid` or `Handsontable` for spreadsheet-style screens
- `TanStack Query` for server state
- `Zustand` or light state store for screen-local draft state

Required UX patterns:

- spreadsheet-first editable tables
- sticky headers and frozen columns
- side-by-side document and data entry
- cell-level formula trace
- diff views for revisions
- warnings for mismatch between imported docs and entered values

Primary frontend modules:

1. Contract dashboard
2. Contract setup wizard
3. Schedule and item master editor
4. MB review screen
5. Bill review screen
6. Recoveries screen
7. Index management screen
8. PVC run builder
9. Export/report center
10. Audit trail and revision browser

### 6.3 Backend Architecture

Recommended:

- `FastAPI` for backend APIs
- Python domain engine for PVC and document processing
- background jobs via `RQ` or `Celery`
- Redis for queue/cache

Reason:

- Python is the pragmatic choice for Excel parity, PDF parsing, and calculation fidelity
- domain math and import tooling will be faster to build and validate in Python

Backend bounded modules:

1. Auth and tenancy
2. Contract setup
3. Document ingestion
4. Parsing and normalization
5. Measurement and billing domain
6. PVC rules engine
7. Calculation engine
8. Export service
9. Audit/versioning service
10. Notification/task service

### 6.4 Database Design

Recommended database:

- `PostgreSQL`

Store:

- normalized contract/bill/measurement entities
- JSONB for parsed document payloads
- immutable snapshots for each calculation run
- event/audit tables

Suggested table groups:

- `tenants`, `users`, `roles`, `memberships`
- `contracts`, `tenders`, `agreements`, `schedules`, `contract_items`
- `measurement_books`, `measurement_lines`
- `bills`, `bill_lines`, `bill_recoveries`
- `index_series`, `index_observations`
- `pvc_rule_sets`, `pvc_rule_versions`
- `pvc_runs`, `pvc_component_results`
- `documents`, `document_versions`, `document_extractions`
- `approvals`, `comments`, `tasks`
- `audit_events`, `snapshots`

### 6.5 API Structure

REST is sufficient for MVP.

Example resource groups:

- `POST /auth/login`
- `GET /contracts`
- `POST /contracts`
- `POST /contracts/{id}/documents`
- `POST /contracts/{id}/parse`
- `GET /contracts/{id}/items`
- `POST /contracts/{id}/bills`
- `POST /contracts/{id}/recoveries`
- `POST /contracts/{id}/indices`
- `POST /contracts/{id}/pvc-runs`
- `GET /pvc-runs/{id}`
- `POST /pvc-runs/{id}/approve`
- `POST /exports/pvc/{run_id}`

### 6.6 Calculation Engine Design

Split the engine into deterministic stages:

1. ingest canonical bill and contract state
2. validate rule completeness
3. derive eligible amount buckets
4. build index snapshot
5. execute formula graph
6. round and format
7. generate trace tree
8. persist immutable run result

Each result should be explainable as:

- source value
- transformation
- formula
- output

### 6.7 Import / Export Systems

#### Import

- PDF upload
- Excel upload
- manual table entry
- semi-structured parser templates

Do not over-automate early. Build:

- parse suggestions
- human confirmation

#### Export

- Excel parity output
- printable PDF summary
- audit sheet
- bill-wise PVC detail sheet
- quarter-wise summary

### 6.8 Audit and Versioning Layer

Mandatory for trust:

- version every rule change
- version every index correction
- version every bill import
- snapshot every PVC run
- preserve source-file linkage
- maintain cell-level provenance

Users must be able to answer:

- which formula version was used
- which indices were used
- whether an extra item was excluded
- when a bill was revised
- who overrode a quantity or rate

### 6.9 Authentication and RBAC

Roles for MVP:

- Org Admin
- Contract Admin
- Billing Operator
- Reviewer
- Read-only Auditor

Later:

- external railway reviewer role
- finance role
- document-processing role

### 6.10 Storage Layer

Use object storage for:

- uploaded PDFs
- original Excel files
- generated exports
- OCR artifacts
- snapshot attachments

Suggested:

- S3-compatible storage

## 7. Edge Cases and Risks

### 7.1 Contractual Edge Cases

1. Extra items introduced mid-contract
- exclude from PVC by default unless explicitly enabled

2. Railway-supplied material
- always excluded if free/fixed-rate as per clause logic

3. Schedule revisions
- current agreement qty can differ from original qty

4. Bill prepared after completion but for earlier execution period
- quarter determination must be explicit

5. retrospective base month correction
- must recalculate from frozen rule version

### 7.2 Billing Edge Cases

1. cumulative qty mismatch across MB and bill
2. measured qty greater than payable qty
3. carried-forward quantity from earlier bill
4. item paid under special condition
5. GST inclusive vs exclusive misunderstanding
6. recoveries applied to bill but not PVC base

### 7.3 Index Edge Cases

1. missing month index
2. revised published index
3. bill date falls before all quarter months are published
4. different commodities published at different times
5. wrong quarter mapping

### 7.4 Formula Risks

1. silent spreadsheet reference error
2. incorrect component weight entry
3. wrong mapping of item to commodity index
4. incorrect exclusion of extra items
5. rate build-up sequence done incorrectly

### 7.5 Safe Handling Rules

The system should:

- block final approval if rule coverage is incomplete
- warn if bill quarter and formula quarter do not match
- warn if extra items exist and no eligibility decision has been recorded
- force explicit handling of revised indices
- preserve prior approved runs instead of mutating them
- support superseding runs, not overwriting them

## 8. MVP Definition

### 8.1 Highest-Value MVP Scope

1. Contract setup
- agreement metadata
- schedules and items
- base month
- PVC applicability
- component weights

2. Document vault
- upload agreement, bill, MB, recovery, workbook

3. Bill and recovery ingestion
- manual plus Excel/PDF-assisted parsing

4. Index master
- maintain monthly published indices

5. PVC engine
- derive `W`
- cement and steel buckets
- quarter-average calculations
- run-by-run snapshots

6. Excel-like UI
- review and override before approval

7. Exports
- Excel
- PDF
- audit trace

### 8.2 What Not to Build Initially

- full mobile MB capture
- OCR-only autonomous extraction
- railway-side collaboration portal
- ERP/accounting integrations
- highly generic workflow builder
- multi-region infra
- advanced AI agents making unattended commercial decisions

### 8.3 Lowest-Complexity Reliable Path

1. import existing contractor Excel and PDF inputs
2. normalize into canonical data
3. calculate PVC deterministically
4. export Excel/PDF matching current working style

This path wins trust faster than a "dashboard-first" strategy.

## 9. Competitive Analysis

### 9.1 Likely Weaknesses in Current Market Tools

- Excel dependence without governance
- formulas are opaque and fragile
- poor handling of revisions
- weak document linkage
- no robust audit history
- poor treatment of contract-specific variations
- limited exception management

### 9.2 Product Opportunities

1. Spreadsheet trust with SaaS governance
2. Document-linked calculations
3. Rule templates by railway zone / tender archetype
4. revision-safe recalculation
5. side-by-side MB -> bill -> PVC reconciliation
6. clear extra-item eligibility controls
7. automated anomaly detection

### 9.3 AI-Assisted Opportunities

Use AI for:

- document classification
- clause extraction
- candidate mapping from bill line to contract item
- MB dimensional parsing suggestions
- anomaly explanation
- report narrative drafting

Do not use AI as the final source of calculation truth.

## 10. Recommended Tech Stack

### MVP

- Frontend: `Next.js`, `React`, `TypeScript`
- Table UX: `AG Grid Enterprise` or `Handsontable`
- Backend API: `FastAPI`
- Calc engine: Python domain package
- Queue: `Redis` + `RQ`
- DB: `PostgreSQL`
- Storage: `S3-compatible object storage`
- Auth: `Clerk` or `Auth0` for speed, or self-hosted session auth if required
- Infra: `Docker`, `Render` or `AWS ECS/Fargate`

### Later Scale

- workflow orchestration for parsing jobs
- read replicas for analytics
- tenant-specific encryption / deployment

## 11. Suggested Implementation Phases

### Phase 1: Contract and PVC Core

- contract setup
- item master
- index master
- manual bill input
- deterministic PVC engine
- Excel/PDF export

### Phase 2: Document-Centric Operations

- PDF/Excel ingestion
- parser review UI
- MB to bill reconciliation
- recovery management
- approval snapshots

### Phase 3: Exception and Revision Control

- revised bills
- revised indices
- superseding PVC runs
- variance analysis

### Phase 4: Intelligence Layer

- clause extraction
- anomaly detection
- auto-mapping suggestions
- portfolio analytics

## 12. Key Unknowns Requiring Domain Interviews

1. exact interpretation of quarter selection relative to bill date vs execution period
2. whether Q4 in the sample should really use row-16 indices or whether there is a domain-specific lag rule
3. whether schedule C extra NS in the 2nd bill was intentionally included or should have been excluded from PVC
4. exact approval workflow between contractor office and railway
5. whether different railway zones use materially different PVC templates
6. treatment of negative PVC and offsets
7. treatment of revised published indices after submission
8. whether recoveries ever directly reduce PVC base in practice
9. how final bill and closed-contract reconciliation is currently performed
10. whether MB is ever contractor-entered vs purely railway-generated

## 13. Long-Term Moat Opportunities

1. Contract-rule knowledge graph
- clause-aware PVC templates by railway/tender type

2. Document-linked audit defensibility
- every output traceable to source page, item, and rule version

3. Historical benchmarking
- compare contracts, bills, and PVC outcomes across a contractor portfolio

4. Anomaly and leakage detection
- detect under-claimed PVC, exclusion mistakes, wrong indices, missed carry-forwards

5. Submission-grade exports
- outputs that become de facto accepted by field teams and reviewers

6. Network effects from rule libraries
- reusable templates for DSR-heavy, NS-heavy, steel-heavy, or repair contracts

## 14. Architecture Conclusions

The correct product is a vertical contract-calculation system with four hard requirements:

1. deterministic calculation traceability
2. spreadsheet-grade user control
3. contract-specific configurable rules
4. immutable audit snapshots

The uploaded sample proves that the domain complexity is not in arithmetic alone. It is in the transformation from contractual and operational documents into an eligible PVC base, and in preserving trust while doing so.
