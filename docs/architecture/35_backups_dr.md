# 35 · Backups and disaster recovery (Ubuntu + droplet + Oracle)

## Targets

| Data                                       | RPO                                                              | RTO                          |
| ------------------------------------------ | ---------------------------------------------------------------- | ---------------------------- |
| Orders, invoices, payments, POD (Postgres) | 5 min (WAL streaming)                                            | 1 h (promote Oracle replica) |
| POD photos and documents (object storage)  | 1 h                                                              | 4 h                          |
| Kafka topics                               | n/a (Postgres is the record; topics are rebuilt from the outbox) | 2 h                          |
| Agent models, LoRA adapters, RAG index     | 24 h                                                             | 8 h (rebuild)                |
| Config / secrets (SOPS in git)             | 0 (git)                                                          | 30 min                       |

## 3-2-1 layout (free)

- **Copy 1 (primary):** the droplet's Postgres is primary for business data, because it must keep running when Ubuntu is off. Ubuntu holds the admin/agent data and the large object store (MinIO).
- **Copy 2 (other host):** streaming replica on the Oracle Always Free VM (ARM, 200 GB block, free). The droplet and Ubuntu cross-replicate their object stores with `rclone`/MinIO mirror.
- **Copy 3 (off-site, different provider):** pgBackRest full weekly + incremental daily + WAL archive, encrypted (AES-256, key in SOPS), stored on Oracle Object Storage (20 GB free) and on an Ubuntu local disk. No paid DigitalOcean backups or Spaces (Ravi, D-BK2). **Monthly offline USB copy** of the encrypted archive, kept off-site (D-BK1).
- **Retention:** daily for 14 days, weekly for 8 weeks, monthly for 7 years for finance tables (ITA s.230 / CRA 6 years plus a margin).

## Drills

- Nightly automated restore of the last backup into a throwaway container, with row counts and invoice totals compared (nightly CI lane, file 32), from week 2.
- Monthly test where Ubuntu is switched off for 4 hours. Merchants, customers, drivers and the website keep working on the droplet. The admin falls back to read-only on Oracle. Week 6 first, then monthly.
- Quarterly failover where the droplet is lost: promote the Oracle replica and switch DNS (Cloudflare free, DNS-only, TTL 60 s, D-PR1). During failover, customers see a "please retry" message and no bookings are queued (D-LB1). Week 13.
- Kafka restore drill (week 13, already in plan).

Existing `porterchain-postgres-backup.{service,timer}` stay, and are re-pointed to pgBackRest in week 2.
