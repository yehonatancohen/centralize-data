---
title: Centralize Data
emoji: 📊
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
---

# Centralize Data

A centralized customer database application for managing contacts, events, and attendance data.

## Features

- **CSV/Excel Upload** — Upload customer data files with automatic column mapping
- **Deduplication** — Smart fuzzy matching to merge duplicate contacts
- **Event Tracking** — Track events and attendance with payment information
- **Customer Scoring** — RFM-based scoring with customer segmentation (VIP, Regular, New, Churned)
- **Dashboard** — Overview of customer segments, top customers, and churn alerts
- **Export** — Export filtered customer data

## Environment Variables

Set these as **Secrets** in your Hugging Face Space settings:

| Variable | Description |
|---|---|
| `TURSO_DATABASE_URL` | Your Turso database URL |
| `TURSO_AUTH_TOKEN` | Your Turso authentication token |

## Local Development

```bash
pip install -r requirements.txt
python run.py
```
