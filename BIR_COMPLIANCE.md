# UpScale POS BIR Accreditation Checklist

This repository implements technical controls intended to support an application
under RMO No. 24-2023, RR No. 11-2024, and RMC No. 77-2024. Software controls
alone do not grant BIR accreditation or a Permit to Use.

## Implemented Controls

- Six-digit sequential invoice series with reset-counter rollover.
- Seller, branch, MIN, machine/license, accreditation, PTU, supplier, and
  software-version metadata captured permanently on each invoice.
- Registered taxpayer name separated from business/trade name.
- Buyer name, address, TIN, and business style fields.
- Cash tendered and change accountability.
- VATable, VAT-exempt, zero-rated, VAT, SSPT, and discount fields.
- SC, PWD, NAAC, and Solo Parent beneficiary records and sales-book export.
- Printable Invoice output and tracked reprints marked `REPRINT`.
- Voids retained with mandatory reason, operator, timestamp, and stock reversal.
- Invoice and adjustment lock after the Z-Reading for a business date.
- X-Reading, Z-Reading, cash totals, accumulated grand total, Z-counter, and
  reset counter.
- Daily E-Journal containing invoice, void, X-Reading, and Z-Reading details.
- Hash-linked activity log covering writes, logins, readings, exports, and
  reprints, with an integrity verification endpoint.
- Configurable Philippine business-day rollover.
- PostgreSQL/Supabase-compatible SQLAlchemy configuration and Alembic
  migrations.

## Required Before Filing

1. Confirm the exact invoice layout and tax treatment with the taxpayer's RDO
   and accountant. Product tax classification remains taxpayer-controlled.
2. Assign the final immutable software version to be demonstrated.
3. Complete all registration fields in Settings using issued documents. Never
   invent an accreditation number, MIN, or PTU.
4. Prepare the Enhanced eAccReg enrollment and accreditation documents,
   notarized sworn statement, system architecture, user manual, sample Invoice,
   X-Reading, Z-Reading, E-Journal, backend reports, and activity log.
5. Demonstrate stock sale, void, reprint, X-Reading, Z-Reading, post-Z blocking,
   power/network recovery, backup restoration, and audit-integrity verification.
6. Obtain the Certificate of Accreditation for the exact software version.
7. Register every deployed terminal and obtain its PTU and MIN before issuing
   official invoices.
8. Configure managed PostgreSQL backups and document restoration testing and
   record-retention responsibilities.
9. File required notices with the RDO for invoice-series conversion, reset
   events, major enhancements, retirement, or cancellation when applicable.

## Deployment Rules

- Production requires `DATABASE_URL`, `SECRET_KEY`, `JWT_SECRET_KEY`, and
  `CORS_ORIGINS`.
- Use a PostgreSQL role that cannot drop or alter production tables during
  normal application operation.
- Restrict database administration to named personnel and retain provider audit
  logs.
- Do not deploy a major feature or database change under an accredited version
  without determining whether reaccreditation is required.
- Product images currently use local Flask storage. Move them to Supabase
  Storage before deploying on an ephemeral host.
- The physical scale uses an outbound Raspberry Pi transfer bridge. The hosted
  backend accepts only authenticated, stable, and recent readings.

## Important Tax Limitation

The system records statutory discount documentation and an operator-approved
discount amount. Eligibility and computation can vary by product and governing
law. The taxpayer and accountant must validate the configured product tax
classifications and discount procedure before accreditation and production use.
