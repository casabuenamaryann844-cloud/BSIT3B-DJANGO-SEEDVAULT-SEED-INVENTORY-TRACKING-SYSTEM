# SeedVault Documentation
**Seed Inventory Tracking System — BSIT-3B**

Welcome to the SeedVault project documentation directory. All core architectural specifications, plans, user role guides, and domain research are organized below:

---

## Documentation Index

| Document | Purpose & Key Topics |
| :--- | :--- |
| 📄 [`PLAN.md`](./PLAN.md) | **Master System Architecture & Roadmap**: Overall system workflow flowchart, ER diagram, role-based permission matrix, and full 6-phase master implementation checklist. |
| 🌾 [`SEED_VARIANTS.md`](./SEED_VARIANTS.md) | **Seed Variety & Storage Architecture Guide**: How crops, varieties, and harvest batches are modeled, flat vs. hierarchical 3-tier models, UI datalist patterns, and stock aggregation queries. |
| 🔐 [`ACCOUNTS.md`](./ACCOUNTS.md) | **Role-Based Authentication & Governance**: Administrator, Staff, and Instructor permission levels, public registration workflow, admin access code verification, and security rules. |

---

## System Quick Reference

- **Django Project Configuration**: [`mysite/settings.py`](../mysite/settings.py)
- **Core Inventory Models**: [`apps/core/models.py`](../apps/core/models.py)
- **User Governance Views**: [`apps/users/views.py`](../apps/users/views.py)
- **Distribution Views**: [`apps/info/views.py`](../apps/info/views.py)

