# SocietyPay — Society Maintenance Automation Demo

A portfolio-ready Streamlit application for housing society maintenance billing, simulated payment processing, invoice tracking, reconciliation and reporting.

> **DEMO ONLY — NO REAL MONEY.** All people, bank-style transactions and payment outcomes are fictional. This is not a production payment service.

## Features

- 200 seeded demo flats/residents
- Monthly invoice generation
- Overview metrics and collection chart
- Resident/flat directory and add-resident form
- Invoice/payment history and CSV exports
- Mock checkout with Success, Failed and Pending outcomes
- Demo receipt export
- Manual matching of sample bank transactions to invoices
- Monthly collection reporting
- Reset demo database button

## Run locally

Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The SQLite database is created automatically as `societypay.db`.

## Deploy free with Streamlit Community Cloud

1. Create a GitHub repository named `societypay-demo`.
2. Upload `app.py`, `requirements.txt`, and the `.streamlit/config.toml` file. Do not upload `societypay.db`.
3. Sign in at https://share.streamlit.io/ using GitHub.
4. Choose **Create app**, select your repository and branch, and set the main file path to `app.py`.
5. Click **Deploy**. Streamlit will install dependencies from `requirements.txt`.

Official instructions: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## Important hosting note

This demo uses local SQLite. On free ephemeral hosting, data can reset when the app is restarted/rebuilt and it is not appropriate for durable production records. For a real multi-user deployment, use a managed PostgreSQL database, authentication, backups, authorization, audit logs, and a payment gateway's approved flow. Never store card data or mark invoices paid based only on a browser redirect.

## Payment integration

The current app uses a mock gateway only. A future Razorpay/Cashfree test-mode integration should create orders on the server, verify signed webhooks, handle duplicate webhook deliveries idempotently, distinguish payment success from settlement, and keep society funds in a provider-approved settlement arrangement. Do not use real API keys in source control.
