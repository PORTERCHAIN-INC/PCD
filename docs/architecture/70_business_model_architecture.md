# 70. Business model architecture: one Organisation model (Phase 0, L35)

Status: plan (docs only). D-70-1, D-70-2 and D-70-3 decided yes by Ravi on 29 Oct 2026. D-70-4 decided by Ravi on 29 Oct 2026 with a changed scope (all medicine types, §7a).
Order of design and build: Shopify merchant → warehouse/3PL/storage → small local shop → courier partner → logistics partner → supply chain → import/export / customs broker (CHA) → retail customer.

## 1. Problem (evidence, 29 Oct 2026)

- The code models two personas: `merchants` (+ 12 `merchant_*` tables: `merchant_users`, `merchant_api_keys`, `merchant_webhooks`, `merchant_webhook_deliveries`, `merchant_contracts`, `merchant_documents`, `merchant_recipients`, `merchant_booking_templates`, `merchant_merges`, `merchant_alerts`, `merchant_audit_logs`, `merchant_api_usage_logs`) and `customers` (+ `customer_addresses`, `customer_consents`, `customer_credits`, `customer_notes`). `merchant_models.py` alone has 242 column definitions.
- Warehouses, couriers, logistics, supply chain and CHA have nowhere to live except "merchant" with free-text notes, or a lead row. Per-business behaviour is hard-coded (e.g. `merchant_engine/kaylulu_template.py` is a one-merchant template in code).
- External keys are ad hoc: `external_ref` on stops (`schemas_merchant.py:364`), Shopify idempotency key `shopify:{shop}:{order_id}` (`shopify_payload_ops.py:290`), no per-org uniqueness rule.

## 2. Decision D-70-1 (recommended): one `organisation` + `business_type` + capability profile

Every party that is not a person is an **Organisation**. A retail customer is a **person** who may optionally belong to a personal org (auto-created, invisible). Behaviour is driven by **capabilities**. **A new business type that reuses existing capabilities is config only**: a `business_type` row with default capabilities, rate card, copy and onboarding fields, and no new code or tables. **A new capability or document is a new module**, with its own code, migration, templates and tests (§2.2). Separate persona tables per business type were rejected: 8 types × the same 12 tables = schema explosion and duplicate code; a single `merchants` table with flags was rejected because partners (who _receive_ jobs) and shippers (who _send_ jobs) need different relations.

Two roles an org can play (both allowed at once, e.g. a 3PL that ships for clients and also takes our overflow):

- **Shipper** (sends us work): Shopify merchant, small shop, warehouse, supply chain, CHA, retail.
- **Partner** (does work for us, broker model doc 56): courier, logistics, warehouse (storage/cross-dock), CHA (clearance).

### 2.1 Business types and default capability profile

| business_type                                                                          | Role                | Default capabilities (on)                                                                      | Pickup mode default             | Label mode          | Tracking mode        | Price card               |
| -------------------------------------------------------------------------------------- | ------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------- | ------------------- | -------------------- | ------------------------ |
| `shopify_merchant`                                                                     | shipper             | shopify_app, carrier_rates (plan-gated), parcel, invoicing_interac, webhooks                   | scheduled_daily (cut-off 14:00) | ours_4x6            | both (their order #) | contract or B2B standard |
| `warehouse_3pl`                                                                        | shipper + partner   | multi_location, dock_appointment, pallet, csv_import, api, their_label_accept, storage_partner | dock_appointment                | both + relabel rule | both                 | pallet/route card        |
| `small_shop` (subtype: pet_food, flowers, pharmacy, bakery_cake, gift, candles, other) | shipper             | on_demand, same_day, fragile/perishable handling, simple portal, email_to_order                | on_demand                       | ours_4x6            | ours                 | small-shop card          |
| `courier_partner`                                                                      | partner             | partner_portal, job_accept, pod_upload, rate_card_inbound, coi_required                        | n/a (they pick up)              | theirs or ours      | theirs primary       | partner card (cost)      |
| `logistics_partner`                                                                    | partner (+ shipper) | partner_portal, edi_lite, cvor_required, pallet, linehaul                                      | recurring_route                 | theirs              | both                 | partner card             |
| `supply_chain`                                                                         | shipper             | api, recurring_route, multi_location, sla_contract, edi_lite                                   | recurring_route                 | both                | both                 | contract                 |
| `import_export_cha`                                                                    | shipper + partner   | port/rail pickup, bonded_note, document_pack (CCI, CAD ref), edi_lite                          | dock_appointment                | theirs              | theirs primary       | contract                 |
| `retail_customer`                                                                      | shipper (person)    | stripe_card, web/app booking                                                                   | on_demand                       | ours                | ours                 | retail card              |

Subtype rules (small shops): `pharmacy` → `rx_delivery=true` with the `controlled_substance` handling profile (§7a). PorterChain is the official delivery agent for local pharmacies, covering all medicine types including prescriptions and controlled substances. The pharmacy stays the dispenser and stays responsible., `bakery_cake` → `food_handling=true` (clean insulated bag, upright, no stacking, ≤ 2 h door to door), `flowers` → `perishable`, `upright`, `pet_food` → heavy bag weight bands, `candles` → `heat_sensitive` advisory in summer.

### 2.2 Documents & capabilities matrix (Ravi 29 Oct 2026: "a bakery has no bill of lading, a warehouse sometimes does")

Business types share one system, but each **sees only its own documents and capabilities**. **A** = Always, **C** = Conditional (rule number below), **–** = Off (module not available to that type).

| Type / subtype                     | BOL | Pallet manifest | Customs docs (CBSA CAD (ex-B3) / CARM, commercial invoice) | POD | Rx custody log    | Cold-chain temp log | TDG declaration | Packing slip | Labels               | Signature / ID                   | 2-person | Pallets | Bulk upload / API     |
| ---------------------------------- | --- | --------------- | ---------------------------------------------------------- | --- | ----------------- | ------------------- | --------------- | ------------ | -------------------- | -------------------------------- | -------- | ------- | --------------------- |
| shopify_merchant                   | C1  | –               | –                                                          | A   | –                 | C6                  | –               | C8           | ours / C9            | C10                              | C11      | –       | A (Shopify app + API) |
| warehouse_3pl                      | C1  | C2              | –                                                          | A   | –                 | C6                  | C7              | C8           | C9 (theirs default)  | C10                              | C11      | C3      | A                     |
| small_shop: bakery_cake            | –   | –               | –                                                          | A   | –                 | C6                  | –               | –            | ours                 | –                                | –        | –       | – (email-to-order)    |
| small_shop: flowers                | –   | –               | –                                                          | A   | –                 | –                   | –               | –            | ours                 | –                                | –        | –       | –                     |
| small_shop: pet_food               | –   | –               | –                                                          | A   | –                 | –                   | –               | C8           | ours                 | –                                | C11      | –       | –                     |
| small_shop: pharmacy               | –   | –               | –                                                          | A   | A (C5 sets level) | C6                  | –               | –            | ours (no drug names) | A (ID + patient/agent signature) | –        | –       | –                     |
| small_shop: gift / candles / other | –   | –               | –                                                          | A   | –                 | –                   | –               | C8           | ours                 | C10                              | –        | –       | –                     |
| supply_chain                       | C1  | C2              | C4                                                         | A   | –                 | C6                  | C7              | C8           | C9                   | C10                              | C11      | C3      | A                     |
| import_export_cha                  | C1  | C2              | C4                                                         | A   | –                 | –                   | C7              | C8           | C9                   | C10                              | C11      | C3      | C12                   |
| courier_partner                    | C1  | –               | –                                                          | A   | C5                | C6                  | –               | –            | C9                   | C10                              | –        | –       | A (job feed)          |
| logistics_partner                  | C1  | C2              | C4                                                         | A   | –                 | C6                  | C7              | –            | C9                   | C10                              | C11      | C3      | A (EDI-lite)          |
| retail_customer                    | –   | –               | –                                                          | A   | –                 | –                   | –               | –            | ours                 | C10                              | C11      | –       | –                     |

**Rules:**

- **C1 BOL:** the order contains a pallet (P band), freight over 150 kg, a B2B LTL/linehaul leg, a handoff to a partner carrier, **or any shipment over 45 kg that leaves the local municipality** (the legal minimum, e.g. an XL sofa from Toronto to Mississauga). **Otherwise never on parcel bands XS–XL.** Bakery, flowers and pharmacy orders are capped at 45 kg per shipment, so they never trigger it. Legal basis: O. Reg. 643/05 s. 4 (exempt for parcels ≤ 45 kg and for carriage solely within one municipality), §2.3. A warehouse therefore sees BOL on a pallet or LTL order and not on a parcel order.
- **C2 Pallet manifest:** 2 or more pallets on one order or route.
- **C3 Pallets:** the org has the `pallet` capability and the order uses the P band. The vehicle must be a van, truck or partner (no Civic, doc 79 §0).
- **C4 Customs docs:** a cross-border leg or an in-bond/bonded movement. We **capture** the importer's CAD (Commercial Accounting Declaration, which replaced the B3 on 21 Oct 2024) transaction number and CARM reference and carry the CBSA commercial invoice/CCI. **We never file customs entries**; the licensed customs broker/CHA files in CARM.
- **C5 Rx custody log:** controlled substances and monitored drugs get the full log (70 §7a: seal id, count, every handoff). Other Schedule I Rx gets the signature log only. A courier partner sees it only if we hand them a pharmacy job, which is off in Phase 0.
- **C6 Cold-chain temp log:** an item is flagged 2–8 °C or frozen (e.g. a cream cake, insulin, meal kits). It records logger readings at pickup and drop.
- **C7 TDG declaration:** the item is declared dangerous goods **and** the org and driver hold TDG training. Otherwise the order is refused. Off for small shops and retail; lithium batteries and aerosols are declared through this module.
- **C8 Packing slip:** the merchant turns it on, or the order has line items they send.
- **C9 Their labels:** `label_mode = theirs/both` (§4). Otherwise we print ours.
- **C10 Signature / ID:** declared value over $500, the merchant's setting, or the customer requests it. Pharmacy is always A.
- **C11 2-person:** furniture class F4, a single item over 50 kg, or the customer picks the add-on (doc 72 §8).
- **C12 Bulk upload / API for CHA:** on when the org has a developer key or uploads CSV.

**Each document is a separate module** (`doc_bol`, `doc_pallet_manifest`, `doc_customs_pack`, `doc_pod`, `doc_rx_custody`, `doc_cold_chain`, `doc_tdg`, `doc_packing_slip`, `label_*`). Each has its own templates, table and tests.

- **On for an org** only if its capability is enabled. **On for an order** only if the rule above evaluates true at quote time; the result is stored on the order as `required_documents[]`.
- **Hidden everywhere when off:**
  - In the UI, there is no tab, field, button or download for it.
  - In the API, the fields are omitted from responses, and sending them returns `422 capability_not_enabled`.
  - In emails and webhooks, there is no attachment or link.
- **Enforced server-side:** the DBOS order workflow and the SpiceDB caveat `has_capability()` check it, and the PDF render service refuses to generate a document that is not in `required_documents[]`. Front-end hiding is never the only control.
- **Code rule:** a new type that reuses these modules = config only. A new document or capability (e.g. a future `doc_customs_filing`) = a new module, with code, migration and acceptance tests.

### 2.3 Identifiers & milestones (Ravi 29 Oct 2026, pt126u: "pick which is required in Canada for us")

Sources were checked on 29 Oct 2026, and every one is current on its publisher's site.

- **[O. Reg. 643/05 Carriage of Goods](https://www.ontario.ca/laws/regulation/050643)** (HTA, consolidated to 31 Dec 2025). This is the Ontario uniform conditions of carriage regulation. **O. Reg. 363/04 is _Security of Loads_ (cargo securement), not the bill of lading rule.**
- **[CBSA CARM](https://www.canada.ca/en/border-services-agency/services/carm/schedule.html)** and **[D17-1-5](https://www.cbsa-asfc.gc.ca/publications/dm-md/pdf/d17-1-5-eng.pdf)**: the CAD replaced the B3 on 21 Oct 2024, and CARM has been permanent since 1 Jan 2026.
- **[CUSMA proof of origin](https://www.cbsa-asfc.gc.ca/services/cusma-aceum/overview-survol-eng.html)** and **[D11-4-14](https://cbsa-asfc.gc.ca/publications/dm-md/d11/d11-4-14-eng.html)**.
- **[TDG shipping document](https://tc.canada.ca/en/dangerous-goods/required-information-shipping-document)** and **[TDGR s. 1.17](https://laws-lois.justice.gc.ca/eng/regulations/sor-2001-286/section-1.17.html)** (current to 30 Sep 2026).
- **[Ontario CVOR](https://www.ontario.ca/page/commercial-vehicle-operators-registration-cvor)**.
- **LTL practice:** the [NMFTA density-based NMFC changes of 19 Jul 2025](https://www.freightwaves.com/news/new-ltl-freight-class-rules-take-effect-on-saturday) and a Canadian carrier tariff, [Apex Tariff 101](https://www.apexltl.com/forms/TARIFF101-20250414.pdf).

**Filter (Ravi 29 Oct 2026, "whatever we need, just pick that"):** every row below is legally required, protects a claim, or saves money. **Dropped:** PTA, LIFR, AWB/sea waybill, NMFC class, GS1 SSCC issuance by us (we read theirs), HS codes (in the broker's CAD).

**What the law actually says (this drives the L marks below):**

- **BOL / contract of carriage (O. Reg. 643/05 s. 4).** Every general-freight contract of carriage must contain the listed particulars (s. 4(1)(a)–(s)): consignor, consignee, origin, destination, date, carriers, goods, declared value, prepaid/collect, C.O.D., receipt "in apparent good order", signatures and the claim-notice statement. Schedule 1 conditions are _deemed_ terms (s. 4(2)).
  - **There is no "written contract" exemption.** A separate written agreement can only limit liability if the BOL says so conspicuously (s. 4(1)(s)), and alterations must be signed or initialled (Sch. 1 art. 18).
  - **Real exemptions:**
    - s. 4(3)(e): a parcel that does not weigh more than 45 kg.
    - s. 2 para 1: goods carried solely within one local municipality, e.g. a Toronto-to-Toronto order.
    - s. 2 para 10: an operator carrying its own goods, e.g. a bakery's own van.
    - Some commodities (household goods and livestock have their own schedules).
  - **Scope:** it applies to a "public truck", i.e. a commercial motor vehicle carrying another person's goods for compensation. Whether a Honda Civic sedan is a commercial motor vehicle is a **legal-review point (U-ID-1)**. We issue the BOL anyway whenever C1 fires.
- **Cargo insurance (s. 3).** Each vehicle carrying goods for compensation needs cargo liability insurance, and **evidence of it must be carried in the vehicle** (s. 3(3), amended by O. Reg. 386/25). This covers rentals too.
- **Default liability and claims (Sch. 1).** Liability is $4.41/kg unless a value is declared (art. 9–10). The claim notice is due in writing **within 60 days of delivery**, or within 9 months for non-delivery. The final claim is due within 9 months with the paid freight bill (art. 12). The consignor must show correct weights (art. 19).
- **CBSA.**
  - **The CAD (Commercial Accounting Declaration) replaced the B3 on 21 Oct 2024.** It is submitted in CARM by the importer, or by a broker the importer has delegated in the CARM Client Portal.
  - The commercial invoice/CCI is supporting documentation.
  - **CUSMA certification of origin** has no prescribed form (9 minimum data elements) and is needed only to **claim preferential tariff treatment**. It is **waived at a value for duty ≤ CAD 3,300**, but records must still be kept.
  - A highway carrier that crosses the border itself also files ACI eManifest. That is Off in Phase 0, since we never drive the border leg.
- **TDG.** A shipping document is **always required for dangerous goods unless an exemption applies**. The main one is **limited quantity, s. 1.17**: outer package ≤ 30 kg, Schedule 1 col. 6(a) limits, diamond mark. Under that exemption, Parts 3–8 (shipping document, marks, training) do not apply.
- **CVOR.** It is required for trucks plated in Ontario, the US or Mexico with an **RGW or actual weight over 4,500 kg**, and that **includes rented trucks**. The individual personal-move lease exemption does not cover business use. The Civic and cargo vans of 4,500 kg or less are exempt.
- **LTL classification.** NMFC is the NMFTA's (US) classification. Since 19 Jul 2025 it is primarily density-based, with 13 density subprovisions. Canada has no formal national class system: domestic LTL is priced on weight, dimensions, cube/density and linear foot, and some Canadian tariffs reference the NMFC 100 Series only for packaging rules.

**Legend:**

- **L** = legally required, with the condition and citation.
- **R** = recommended: our standard, needed for claims, metrics or partner integration.
- **N** = not needed now (field hidden).
- **Types:**
  - **Shop** = shopify_merchant, small_shop (all subtypes) and retail_customer.
  - **WH** = warehouse_3pl.
  - **SC** = supply_chain.
  - **CHA** = import_export_cha.
  - **Partner** = courier_partner and logistics_partner (as carrier for us).

| Identifier / milestone                         | Shop                                                           | WH                                                                | SC                                                      | CHA                                                               | Partner                                        | Condition and source                                                                                                  |
| ---------------------------------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------- | ----------------------------------------------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| BOL no. (contract of carriage)                 | N (parcels ≤ 45 kg / same municipality: exempt); R if C1 fires | L when > 45 kg and inter-municipal; else R (C1)                   | same as WH                                              | same as WH                                                        | L on every handoff we tender to them (> 45 kg) | O. Reg. 643/05 s. 2, s. 4. Our BOL no. = `BOL-{yyyy}-{seq}`. U-ID-1 for the Civic                                     |
| POD (clean / noted with OS&D)                  | R (Always, every order, our policy)                            | R                                                                 | R                                                       | R                                                                 | R (required from partner by contract)          | Not a statute. It is the evidence for the 60-day claim notice (Sch. 1 art. 12) and "apparent good order" (s. 4(1)(o)) |
| PO number                                      | N (R if the merchant sends one)                                | R                                                                 | R                                                       | R                                                                 | N                                              | Buyer's reference; needed for OTIF matching                                                                           |
| SKU / UPC / GTIN                               | R only with line items (C8)                                    | R                                                                 | R                                                       | R (HS code lives in the broker's CAD)                             | N                                              | Needed to prove "short" on an OS&D claim. No legal duty on the carrier                                                |
| Packing slip                                   | C8 (R)                                                         | R                                                                 | R                                                       | R                                                                 | N                                              | Commercial practice                                                                                                   |
| Seal no.                                       | N (pharmacy: tamper seal id, 70 §7a, R)                        | R on sealed FTL/trailer                                           | R on sealed FTL                                         | R on container / in-bond (the broker confirms CBSA seal terms)    | R when the trailer is sealed                   | Must match the BOL at delivery; a mismatch records OS&D                                                               |
| PRO no.                                        | N                                                              | R **only when handing to an LTL carrier**                         | same                                                    | same                                                              | captured from the LTL carrier                  | Carrier-assigned. Never generated by us                                                                               |
| LPN / SSCC pallet barcode                      | N                                                              | R per pallet (C3)                                                 | R                                                       | R                                                                 | N                                              | GS1 SSCC-18 when the shipper has a GS1 prefix, else our LPN                                                           |
| Vehicle plate + VIN (every trip, incl. rental) | R (our rule, every trip)                                       | R                                                                 | R                                                       | R                                                                 | R (theirs)                                     | L in effect for CVOR vehicles > 4,500 kg (fleet incl. rented); cargo-insurance evidence in each vehicle, s. 3(3)      |
| Gross / tare / net weight                      | R gross (declared)                                             | L gross weight on the BOL (Sch. 1 art. 19); R tare/net per pallet | same                                                    | same                                                              | same                                           | The vehicle must not exceed its RGW (CVOR page). Rescale fees apply to wrong BOL weights (carrier tariffs)            |
| ETA / ETD / ATA / ATD                          | R                                                              | R                                                                 | R                                                       | R                                                                 | R                                              | Feeds OTIF and dwell (79 §6a)                                                                                         |
| Dwell time                                     | R (computed)                                                   | R                                                                 | R                                                       | R                                                                 | R                                              | ATD − ATA per stop (79 §6a)                                                                                           |
| OTIF                                           | R                                                              | R                                                                 | R                                                       | R                                                                 | R (partner SLA)                                | 79 §6a                                                                                                                |
| OS&D claims                                    | R                                                              | R                                                                 | R                                                       | R                                                                 | R                                              | Timelines from Sch. 1 art. 12; liability $4.41/kg or declared value                                                   |
| Incoterms                                      | N                                                              | N                                                                 | R if cross-border                                       | R (import/export only)                                            | N                                              | Record only (ICC Incoterms 2020)                                                                                      |
| Commercial invoice / CCI ref                   | N                                                              | N                                                                 | L for the importer when cross-border (we record only)   | L for the importer (we record only)                               | N                                              | CBSA D17-1-5 supporting docs                                                                                          |
| CUSMA certification of origin ref              | N                                                              | N                                                                 | L only if claiming CUSMA preference and VFD > CAD 3,300 | same (record only)                                                | N                                              | CBSA D11-4-14 ¶6–8                                                                                                    |
| CAD (ex-B3) transaction no.                    | N                                                              | N                                                                 | L for the importer when importing (record only)         | L for the importer/broker (record only; the broker files in CARM) | N                                              | CARM; we never file (C4)                                                                                              |
| TDG shipping document                          | N (DG refused, C7)                                             | L if DG not under an exemption (e.g. s. 1.17 LQ)                  | same                                                    | same                                                              | L if DG                                        | TC TDG; C7 refuses without training                                                                                   |
| CVOR no.                                       | N (Civic and vans ≤ 4,500 kg)                                  | L if any truck or rental > 4,500 kg                               | same                                                    | same                                                              | L (theirs, checked at onboarding, 71)          | Ontario CVOR page                                                                                                     |

**Excluded (not modelled):**

- **AWB / sea waybill:** we do not move air or ocean freight. The airline or ocean line issues these. A CHA can paste one as a free-text external ref on the CHA pack; there is no module.
- **NMFC freight class:** it is the US NMFTA system, and Canadian domestic LTL is priced on weight, dimensions, cube and density. We store L×W×H and weight, so density (lb/ft³) is computed if a US cross-border LTL partner ever needs a class. That would be a new module (§2 code rule).

**Data model (doc 63 schemas; one migration in `ordering` and `dispatch`, Phase 0 wk 3–5):**

- `ordering.shipment_refs`: (order_id, kind enum{bol, po, packing_slip, seal, pro, incoterm, cci, coo, cad, tdg_doc, awb_ext}, value, issuer enum{us, shipper, carrier, broker}, doc_url, created_at). Unique (kind, value, issuer) per org. `pro` is allowed only when the order has an `ltl_carrier_handoff` leg; `cci/coo/cad/incoterm` are allowed only on CHA/SC cross-border orders. Each kind is gated by `required_identifiers[]`, evaluated at quote time like `required_documents[]`, and the same hiding/422 rules apply.
- `ordering.order_lines`: + sku, gtin (GTIN-8/12/13/14, check digit validated), qty_ordered, qty_shipped, qty_delivered.
- `ordering.handling_units`: (lpn, sscc char(18) with check digit, pallet gross/tare/net kg, L×W×H cm, seal_no).
- `dispatch.trips`: + vehicle_plate, vehicle_vin (17 chars, ISO 3779 check digit), is_rental, rental_agreement_ref, rgw_kg, cvor_required (rgw_kg > 4500), insurance_evidence_ref. **NOT NULL before the trip can start**, including for rentals.
- `dispatch.stop_events`: (stop_id, kind enum{etd, eta, pta, ata, atd}, ts timestamptz, source). Dwell is derived (`atd − ata`).
- `ordering.pod`: + status enum{clean, noted}, osd_type enum{over, short, damaged}[], qty, photo_urls, consignee_name, signature.
- `ordering.osd_claims`: (pod_id, type, amount_claimed_cents, notice_deadline = delivered_at + 60 d, final_deadline = shipped_at + 9 months, liability_cap_cents = max(declared_value, 4.41 × kg), status, recovered_cents).

## 3. Data model (schema `org`, doc 63 domain schemas)

```mermaid
erDiagram
  organisation ||--o{ org_capability : has
  business_type ||--o{ organisation : classifies
  business_type ||--o{ capability_default : seeds
  organisation ||--o{ location : has
  organisation ||--o{ contact : has
  organisation ||--o{ membership : has
  person ||--o{ membership : "is member"
  organisation ||--|| operating_profile : configures
  organisation ||--o{ integration : connects
  integration ||--o{ api_credential : issues
  integration ||--o{ webhook_endpoint : notifies
  organisation ||--o{ rate_card_assignment : priced_by
  rate_card ||--o{ rate_card_assignment : assigned
  rate_card ||--o{ rate_line : contains
  organisation ||--o{ contract : signs
  contract ||--o{ rate_card_assignment : governs
  organisation ||--o{ label_profile : prints
  organisation ||--o{ external_ref : owns
  order ||--o{ external_ref : "mapped by"
  organisation ||--o{ order : ships
  organisation ||--o{ partner_job : performs
  organisation ||--o{ ticket : raises
  organisation ||--o{ consent_record : accepts

  organisation { uuid id PK
    text public_id UK "ORG-XXXXXX"
    text legal_name
    text display_name
    text business_type FK
    text subtype
    text role_flags "shipper|partner"
    text status "enum: lead,trial,active,suspended,offboarded"
    text locale "en|fr"
    text gst_hst_number "asked at first invoice"
    uuid parent_org_id FK "group/brand"
    timestamptz created_at }
  business_type { text code PK
    text label_en
    text label_fr
    jsonb default_profile }
  org_capability { uuid org_id PK,FK
    text capability PK
    bool enabled
    jsonb params
    text source "default|ravi|contract" }
  location { uuid id PK
    uuid org_id FK
    text kind "pickup|dock|store|warehouse|billing"
    text address_json
    text fsa
    jsonb hours
    text dock_notes }
  contact { uuid id PK
    uuid org_id FK
    text role "ops|billing|tech|owner"
    text email
    text phone }
  person { uuid id PK
    text keycloak_sub UK
    text email UK
    text locale }
  membership { uuid org_id PK,FK
    uuid person_id PK,FK
    text role "owner|admin|ops|billing|developer|viewer" }
  operating_profile { uuid org_id PK,FK
    text pickup_mode
    jsonb pickup_params
    text tracking_mode "ours|theirs|both"
    text label_mode "ours|theirs|both"
    jsonb relabel_rule
    text_array barcode_formats
    jsonb ref_schema
    int version }
  integration { uuid id PK
    uuid org_id FK
    text kind "shopify|api|csv|email|portal|edi_lite"
    text status
    text external_account "shop domain etc"
    jsonb config }
  api_credential { uuid id PK
    uuid integration_id FK
    text key_prefix UK
    text secret_hash
    text_array scopes
    text env "sandbox|live"
    timestamptz revoked_at }
  webhook_endpoint { uuid id PK
    uuid integration_id FK
    text url
    text secret_hash
    text_array events }
  external_ref { uuid id PK
    uuid org_id FK
    text ref_type "order|shipment|sku|parcel|customer|po|container"
    text ref_value
    text entity_type
    uuid entity_id
    text source "shopify|api|csv|label_scan" }
  rate_card { uuid id PK
    text code UK
    text audience "retail|b2b|partner_cost"
    int version
    date valid_from }
  rate_line { uuid id PK
    uuid rate_card_id FK
    text kind "band|zone|addon|minimum"
    jsonb rule
    int cents }
  rate_card_assignment { uuid org_id FK
    uuid rate_card_id FK
    uuid contract_id FK
    date valid_from }
  contract { uuid id PK
    uuid org_id FK
    text kind "shipper|partner"
    jsonb terms "cancellation_fee, liability, payment_days"
    text doc_version
    date signed_at }
  label_profile { uuid id PK
    uuid org_id FK
    text format "zpl|pdf"
    text size "4x6"
    text barcode "code128|qr|gs1_128"
    jsonb fields }
```

Key rules:

- **Unique keys:** `external_ref (org_id, ref_type, ref_value)` UNIQUE. Their primary key is never ours; ours is `order.public_id` = `PC-YYMM-XXXXXX` (unique, Crockford base32, no O/I/L) and appears on every record, label, tracking page, email and webhook beside their ref.
- **Idempotent upsert:** every inbound create is `INSERT … ON CONFLICT (org_id, ref_type, ref_value) DO UPDATE` guarded by `Idempotency-Key`; replay returns the same `PC-` id (doc 74 §4).
- Status columns are Postgres enums (gate G13). Money is integer cents. All org-scoped tables carry `org_id` with row-level security keyed on the Keycloak token's org claim.

## 4. Operating profile (per org, configurable; no custom code per org, only existing modules switched on)

Set by the onboarding wizard (doc 71 §5) with business-type defaults so most users only press **Looks right**.

| Field             | Options                                                                                                                                                                                                         | Effect                                                                                                          |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `pickup_mode`     | `scheduled_daily` (days, window, cut-off), `on_demand`, `recurring_route` (RRULE, stops), `hub_dropoff` (our hub, hours), `dock_appointment` (slot length, booking lead), `multi_location` (per-location mode)  | Dispatch creates pickup tasks; cut-off decides same/next day; Today page groups by mode                         |
| `ref_schema`      | which of their keys we store: order, shipment, sku, parcel, po, container; label for each ("Order #", "BOL #")                                                                                                  | Shown in their language on our UI; searchable everywhere                                                        |
| `tracking_mode`   | `ours`, `theirs` (their ref as headline, ours small), `both`                                                                                                                                                    | Tracking page `/t/{ref}` accepts PC- id, their ref (scoped by org slug or email verify), or their label barcode |
| `label_mode`      | `ours` (we print ZPL/PDF 4x6), `theirs` (accept their label, driver scans its barcode, we bind it to PC- id), `both` + `relabel_rule` (e.g. relabel when their barcode is unreadable or not Code128/QR/GS1-128) | Label service + driver app scan step                                                                            |
| `barcode_formats` | `code128`, `qr`, `gs1_128` (SSCC-18 for pallets)                                                                                                                                                                | Scanner whitelist; parse rules                                                                                  |

Profile changes are versioned (`operating_profile.version`); orders store the profile version they were created with.

## 5. How capabilities drive the system

| Layer                 | Mechanism                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UI                    | Portal nav and fields render from `org_capability` (e.g. no "Dock appointments" tab unless `dock_appointment`). One portal, not one per type. Labels come from `ref_schema`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| Pricing               | Quote engine picks the org's `rate_card_assignment` (contract first, then business-type card, then retail) (doc 72). Add-ons offered only if capability allows (e.g. `pallet`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| Labels                | `label_profile` + `label_mode`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| Workflows             | DBOS workflows read capabilities at start: `food_handling` adds an upright/insulated checklist step, `controlled_substance` profile adds seal/count scan, ID + patient-or-agent signature POD, no safe-drop, chain-of-custody scans and same-day return (§7a), `dock_appointment` adds a slot booking step, partner capabilities enable `partner_job` routing (doc 56).                                                                                                                                                                                                                                                                                                                           |
| Permissions (SpiceDB) | `definition organisation { relation owner, admin, ops, billing, developer, viewer: person; relation parent: organisation; permission manage = owner + admin; permission ship = manage + ops; permission see_invoices = manage + billing; permission manage_keys = manage + developer; permission view = ship + see_invoices + manage_keys + viewer + parent->view }`, `definition order { relation shipper: organisation; relation partner: organisation; permission view = shipper->view + partner->view_jobs; permission edit = shipper->ship }`, capability checks are a caveat `has_capability(name)` evaluated from the org's flags. Staff roles stay in the `platform` definition (doc 17). |

## 6. Migration from the merchants model (Phase 0 weeks 3–5, with rollback)

1. Create `org.*` tables (Alembic, additive). 2. Backfill: each `merchants` row → `organisation` (`business_type = shopify_merchant` if a Shopify integration exists else `small_shop`/`other` for Ravi to confirm in a one-page review), keeping `organisation.id = merchants.id` so FKs remain valid; `merchant_users` → `person` + `membership`; `merchant_api_keys`/`webhooks` → `integration` + `api_credential`/`webhook_endpoint`; `merchant_contracts` → `contract`; pricing_config JSON → `rate_card` + assignment (Kaylulu schedule `kaylulu-2026-09` becomes a contract rate card, no longer `kaylulu_template.py` code); stop `external_ref` and Shopify keys → `external_ref`. 3. Each customer → `person`; business customers flagged for review. 4. Compatibility views `merchants`, `merchant_users` over the new tables for one release; code moves module by module. 5. Drop the views and old tables when `git grep merchant_id` outside migrations = 0 (new sub-gate of G13). Rollback: views keep the old read path; backfill is reversible because ids are preserved. PCDC and Kaylulu are the first two migrated orgs and are compared field-by-field.

## 7. Decisions for Ravi

- **D-70-1 decided yes** (29 Oct 2026): one Organisation model with business types and capabilities.
- **D-70-2 decided yes** (29 Oct 2026): order id `PC-YYMM-XXXXXX` on everything.
- **D-70-3 decided yes** (29 Oct 2026): an org may be both shipper and partner.
- **D-70-4 decided, CHANGED by Ravi** (29 Oct 2026): pharmacy delivery covers ALL medicine types (OTC, Schedule I prescriptions, monitored drugs and controlled substances). PorterChain is the official delivery agent of local pharmacies; the pharmacy remains the dispenser and is responsible. Handling profile in §7a; pharmacy delivery agreement goes to the lawyer (98 U-70-1).

## 7a. Pharmacy delivery and the controlled-substance handling profile (D-70-4)

**Rules checked 29 Oct 2026:**

- **Ontario College of Pharmacists, Delivery of Prescriptions fact sheet** (https://ocpinfo.com/pharmacy-professionals/practice-topics/fact-sheets/delivery-of-prescriptions/). Dispensing is complete only when the patient or their agent takes custody; until then the drug is in the pharmacy's care and control. Schedule I delivery must be traceable and auditable, with the patient's or agent's signature (wet or electronic). No advance waiver for unattended drop-off is allowed. **A person delivering for the pharmacy cannot be the patient's agent.** Couriers' "no signature" preferences do not apply.
- **Drug and Pharmacies Regulation Act, s.152** (https://www.ontario.ca/laws/statute/90h04): Schedule I (the NAPRA schedule adopted in Ontario) must go by registered mail, or by a method that is traceable and auditable, with a receipt signed by the patient or their agent.
- **Health Canada CS-GD-022, Managing controlled substances** (https://www.canada.ca/en/health-canada/services/health-concerns/controlled-substances-precursor-chemicals/controlled-substances/compliance-monitoring/compliance-monitoring-controlled-substances/guidance-community-pharmacists-pharmacy-technicians/managing-controlled-substances.html):
  - A pharmacist may hire a person or transport company to deliver a prescribed controlled substance. The method must track the substance until the consignee receives it.
  - Health Canada recommends a chain of signatures (name or employee id of everyone handling it). The substance goes only to the patient or their designated person, with proof of delivery and never left unsecured.
  - The pharmacy records sender, recipient, address, dates sent and received, means of transport and product details.
  - **Loss or theft:** the agent must tell the pharmacist immediately. The pharmacist reports to the Office of Controlled Substances within 10 days, whatever the amount.
- **Health Canada CS-GD-005** (https://www.canada.ca/en/health-canada/services/publications/healthy-living/loss-theft-controlled-substances-precursors/reporting-guideline-process.html): the sender (the pharmacy) reports and investigates losses in transit.
- **Transportation of Controlled Substances in Canada** (https://www.canada.ca/en/health-canada/services/health-concerns/controlled-substances-precursor-chemicals/policy-regulations/policy-documents/transportation-of-controlled-substances-in-canada.html): NCR, FDR Part G and BOTSR let pharmacists supply and transport against a prescription. Packaging and labelling are done in the pharmacy.
- **Federal regulations:** the new Controlled Substances Regulations (SOR/2025-242, s.109) are published but marked **"not in force"** (Justice Laws, current to 30 Sep 2026). Until they come into force, the NCR, FDR Part G and BOTSR apply. The design meets both.
- Ontario's Narcotics Safety and Awareness Act, 2010 also applies to monitored drugs (named in the OCP fact sheet).

**`controlled_substance` handling profile** (also applied to monitored drugs; Schedule I Rx uses the same profile without the count and lockbox steps):

1. **Sealed package:** pharmacy-sealed, tamper-evident bag with a unique id and a logged package count, recorded at pickup. PorterChain never opens it and never sees its contents. The pharmacy keeps the product record (CS-GD-022).
2. **No unattended delivery:** no safe-drop, mailbox, concierge or neighbour drop. The app hides those options for this profile.
3. **At the door:** government photo ID check (name match only; no ID number or image stored) plus signature from the patient or the authorised agent named by the patient in advance. The driver can never act as the agent. Exceptions follow the OCP rules (e.g. an "x" witnessed, or an accommodation), and the pharmacy documents them.
4. **Chain of custody:** scan with driver id and timestamp at every handoff: pharmacy → driver → (hub/transfer if any) → recipient. Seal intact is confirmed at each scan.
5. **Failed delivery:** same-day return to the pharmacy, signed back in. Never held overnight by the driver.
6. **In the vehicle:** a locked, fixed lockbox, out of sight; no stops unrelated to the route while a controlled package is aboard.
7. **Cold chain** (insulin, vaccines, biologics): validated insulated container, 2–8 °C, logger reading recorded at pickup and delivery. An excursion is reported to the pharmacy.
8. **Incident or loss:** the driver alerts ops immediately and ops notifies the pharmacist immediately with the custody log. **The pharmacy reports to Health Canada** (10 days). PorterChain keeps its records for at least 2 years and cooperates.
9. **Driver training:** pharmacy-delivery module (privacy/PHIPA, ID and agent rules, seal checks, lockbox, cold chain, incident steps) with a yearly refresher. Only drivers with a clean background check and the training badge get these jobs.
10. **Privacy:** labels show only patient name, address and package id, with no drug names. Drivers see only what is needed (PHIPA agent-of-custodian rules apply via the agreement).

Contract: a **pharmacy delivery agreement** (lawyer list, 98 U-70-1) names PorterChain as the pharmacy's delivery agent and covers custody, records, loss reporting duties, PHIPA, insurance (cargo cover for high-value Rx under G-INS) and audit rights.
