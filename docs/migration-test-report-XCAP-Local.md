# MongoDB → MySQL Migration Test Report

**Run date:** 2026-11-09  
**Source:** MongoDB `XCAP-Local` via the supplied `host.docker.internal:27017` connection  
**Target:** MySQL `XCAP-Local` in the production Compose MySQL container (host port 3308)

## Scope and method

- Discovered all 16 source collections.
- Ran an application dry run, migration, and validation separately for each collection.
- Independently compared exact source document counts and root IDs with MySQL rows. For non-empty root tables, compared all transformed root fields by ID, excluding only the identifier rename (`_id` → `id`).
- Independently compared nested-array row counts and payload multisets, and checked parent foreign-key references.
- Compared planned and actual target columns and foreign keys.
- No code fixes or target cleanup were performed.

## Collection results

| Collection | Source docs | MySQL root rows | Migration | Nested-table results |
|---|---:|---:|---|---|
| `mapping_categories` | 57 | 57 | Passed | `sources` 108/108; `targets` 88/88; payloads and parent FKs matched |
| `ice_trades_xcap` | 1,963 | 1,963 | **Failed, partial writes** | `OrderHistory` 1,999/1,999; `UpdateLogs` 8,099/8,099; `Order.Sources` 1,965/1,965. `OrderHistory.Sources` 293/1,999. Both `*.OrderDetail.TradeDetails` tables contain 0 rows (expected 9,022 and 9,116); child batches were skipped after a parent failure. Root IDs and root payload fields matched. |
| `static_data_entity_config` | 13 | 13 | Passed | No normalized child tables |
| `security_definitions` | 0 | 0 | Passed; no data to verify | Empty source schema; generated ID-only table |
| `user_defined_securities` | 0 | 0 | Passed; no data to verify | Empty source schema; generated ID-only table |
| `download_batches` | 0 | 0 | Passed; no data to verify | Empty source schema; generated ID-only table |
| `role_permissions` | 1 | 1 | Passed | Root ID and all transformed root fields matched |
| `mappings_data` | 182 | 0 | **Failed** | `sources` 0/420 and `targets` 0/341; child batches skipped after the root insert failed |
| `inbound_connections` | 10 | 10 | Passed | `CustomParameters` 26/26; `DefaultSection.Parameters` 140/140; `SessionSection.Parameters` 31/31; payloads and parent FKs matched |
| `system_logs` | 0 | 0 | Passed; no data to verify | Empty source schema; generated ID-only table |
| `app_configuration` | 0 | 0 | Passed; no data to verify | Empty source schema; generated ID-only table |
| `platform_static_data` | 0 | 0 | Passed; no data to verify | Empty source schema; generated ID-only table |
| `outbound_connections` | 5 | 5 | Passed | Root IDs and all transformed root fields matched |
| `connection_heartbeats` | 0 | 0 | Passed; no data to verify | Empty source schema; generated ID-only table |
| `io_mappings` | 9 | 9 | Passed | `OutboundMappings` 9/9; `UpdateLogs` 43/43; payloads and parent FKs matched |
| `trayport_trades_xcap` | 2,162 | 2,162 | Passed | `RawMessages` 2,749/2,749; `SourceTrades` 2,880/2,880; `TargetTradeHistory` 2,891/2,891; `UpdateLogs` 6,893/6,893; payloads and parent FKs matched |

**Summary:** all 16 dry runs completed. 14 migrations completed; 2 failed. Exact independent counts and root IDs/payloads matched for every completed non-empty root table and the root of the partially failed `ice_trades_xcap` migration. Normalized child payloads and FK references matched for all completed child tables.

## Failures and discrepancies

1. **`ice_trades_xcap` — duplicate nested primary keys.** MySQL rejected inserts into `ice_trades_xcap_OrderHistory_Sources` with duplicate primary-key values (error 1062; repeated GUIDs). The parent batch failed after retries, leaving 293 of 1,999 rows in this child table; dependent `TradeDetails` child tables were skipped and remain empty. Other batches/tables had already written, so this collection is partially migrated.
2. **`mappings_data` — invalid JSON for `categoryId`.** MySQL rejected the root insert with error 3140: `Invalid JSON text: "The document root must not be followed by other values."` The field was inferred/projected as JSON but contains values that are not valid JSON documents. No root rows were written; both child tables were skipped.
3. **Application validation count percentages are not reliable in this run.** The app reported values ranging from 5.7% to 646.8%, including for collections whose independently queried exact row counts matched. The MySQL connector obtains counts from `INFORMATION_SCHEMA.TABLES.TABLE_ROWS`, which is an InnoDB estimate rather than an exact count.
4. **Application sample checksum results were `0/N` (or `0/0`).** The validator samples MongoDB randomly but samples MySQL with `LIMIT` and no matching order/IDs. Those independent samples often contain no shared IDs, so the checksum result does not establish a data mismatch. Direct full root ID/payload comparisons were used instead for this report.
5. **Sample-dependent schema discovery.** Empty collections exposed no fields and therefore produced ID-only target tables. `trayport_trades_xcap_TargetTradeHistory` has six additional fields not present in the discovered sample (`EtrmBusinessUnit`, `FirstSequenceID`, `FirstSequenceItemID`, `FirstSequenceItemName`, `SecondSequenceItemID`, `SecondSequenceItemName`); the writer added them dynamically as JSON columns. No planned columns were missing from the tables audited.

## Security and target state

The `inbound_connections` and `outbound_connections` documents include credential-like fields such as `ApiKey`, `Password`, and `Token`; these were copied to the MySQL test target. Values are intentionally not included here. The temporary public Cloudflare tunnel was stopped after testing. At the end of the initial run, no target data had been cleaned up, and `XCAP-Local` contained the successful migrations and partial writes described above. Consider rotating any live credentials present in those source documents.

## Code fixes applied after the test run

The following code issues found during the run were addressed. At the time these fixes were first applied, the live migration was **not rerun** because the target contained partial and successful writes; the subsequent approved rerun is documented below:

- Scalar values mapped to JSON columns are now JSON-encoded before MySQL insertion.
- Normalized child rows now use generated relational primary keys and retain the original embedded ID in a separate JSON column, avoiding collisions when source embedded IDs repeat across parent documents.
- MySQL and MongoDB connectors now provide exact counts for migration scheduling and validation. Validation compares only each source collection/table to its projected root destination table/collection, excluding normalized child tables from collection totals.
- Checksum and aggregate checks now retrieve destination rows by the sampled source primary keys. Checksums run for each selected entity and count source IDs missing from the target; aggregates compare the same source-key cohort.
- The report HTML section heading now explicitly reads “Validation after migration.”

Regression coverage at that stage: the full backend suite passed (61 passed, 2 skipped). A read-only in-memory re-transform of the original `ice_trades_xcap` and `mappings_data` source collections produced no duplicate target IDs and no invalid JSON values.

## Approved rerun after fixes

- **Target reset:** With explicit approval, dropped all 35 existing tables from only the MySQL `XCAP-Local` database. The database itself, other databases, the MongoDB source, and the application metadata volume were preserved.
- **Migration order:** Retested `ice_trades_xcap` and `mappings_data` first, then the remaining 14 collections. All 16 migration jobs completed with zero failed audit entries. The final target contains 35 tables, including the normalized child tables.
- **Exact row counts:** All 16 root-table counts equal their source collection counts. Nested-table counts also match the original independent audit: `ice_trades_xcap` children 1,999 / 9,116 / 1,999 / 9,022 / 1,965 / 8,099; `mappings_data` children 420 and 341; all other populated child-table counts match the earlier table above.
- **Validation issue found and fixed:** The first post-reset validation had exact counts and aggregates but reported only 194/395 matching sample checksums. Runtime inspection showed the validator compared untransformed MongoDB roots (including arrays normalized into child tables) and treated MySQL JSON serialization order as significant. Validation now compares the same transformed root projection written by migration, normalizes SQL numeric/boolean representations, and parses known JSON columns semantically.
- **Final validation:** Read-only validation across all 16 collections reports 100% exact count match, aggregate match, relationships passed, and **395/395** checksums matched; no sampled source IDs were missing from the target. Empty collections had 0/0 sampled rows and exact 0/0 counts.
- **Tests and deployment:** Backend suite: **64 passed, 2 skipped**. The updated production backend container was rebuilt and redeployed successfully; health check passed. The MySQL target is now populated by this successful run—reset it again before any further migration rerun.
- **Credential reminder:** The local target again contains credential-like fields copied from `inbound_connections` and `outbound_connections`. Rotate any real credentials if applicable; no values are recorded in this report.
