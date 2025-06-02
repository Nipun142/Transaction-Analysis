import time
start_time = time.time()


import imaplib
import email
from email.header import decode_header
import pandas as pd
import re
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# === Load environment variables ===
load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
IMAP_SERVER = os.getenv("IMAP_SERVER")
DB_URL = os.getenv("DB_URL")

# === Utility Functions ===
def clean_subject(subject):
    decoded = decode_header(subject)[0]
    if isinstance(decoded[0], bytes):
        return decoded[0].decode(decoded[1] if decoded[1] else "utf-8")
    return decoded[0]

def extract_email_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode(errors="ignore")
    else:
        return msg.get_payload(decode=True).decode(errors="ignore")
    return ""

def parse_transaction(body, transaction_type):
    try:
        amount_match = re.search(r"Amount (Debited|Credited):\s*INR ([\d,]+\.\d{2})", body)
        acc_match = re.search(r"Account Number:\s*(XX\d+)", body)
        dt_match = re.search(r"Date & Time:\s*([0-9\-:, ]+)", body)
        txn_match = re.search(r"Transaction Info:\s*(.*)", body)

        if not amount_match:
            return None

        return {
            "amount": float(amount_match.group(2).replace(",", "")),
            "account": acc_match.group(1) if acc_match else None,
            "datetime": dt_match.group(1).strip() if dt_match else None,
            "description": txn_match.group(1).strip() if txn_match else None,
            "transaction_type": transaction_type
        }
    except Exception as e:
        print("Error parsing email:", e)
        return None

def clean(row):
    l = row['description'].split('/')
    row['datetime'] = pd.to_datetime(row['datetime'], format="%d-%m-%y, %H:%M:%S")
    row['type'] = row['transaction_type']
    row['day'] = row['mail_date'][0:3]
    row['mode'] = l[0]
    row['txn_type'] = l[1]
    row['id']   = l[2]
    row['name'] = l[3]
    row['bank'] = l[4] if row['transaction_type'] == 'Credit' and len(l) > 4 else None
    return row

def get_latest_datetime_from_db():
    engine = create_engine(DB_URL)
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT MAX(datetime) FROM transactions"))
            max_date = result.scalar()
            if max_date:
                return max_date  # Already a datetime object
            else:
                return datetime(2024, 1, 1)  # Default fallback
    except Exception as e:
        print("Error fetching max datetime:", e)
        return datetime(2024, 1, 1)



# === Main Function ===
def main():
    START_DATETIME = get_latest_datetime_from_db()
    END_DATETIME = datetime.now()

    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, PASSWORD)
    mail.select("inbox")

    # IMAP only supports dates, not datetime. Use safe date range
    search_criteria = f'(SINCE "{START_DATETIME.strftime("%d-%b-%Y")}" BEFORE "{(END_DATETIME + pd.Timedelta(days=1)).strftime("%d-%b-%Y")}" FROM "alerts@axisbank.com")'
    status, messages = mail.search(None, search_criteria)
    if status != "OK":
        print("Failed to search emails.")
        return

    email_ids = messages[0].split()
    print(f"📩 Found {len(email_ids)} Axis Bank transaction emails.")

    data_rows = []

    for eid in email_ids:
        status, msg_data = mail.fetch(eid, "(RFC822)")
        if status != "OK":
            continue

        msg = email.message_from_bytes(msg_data[0][1])
        sender = msg.get("From", "")
        subject = clean_subject(msg.get("Subject", ""))
        mail_date = msg.get("Date", "")
        body = extract_email_body(msg)

        if "debited" in subject.lower():
            txn = parse_transaction(body, "Debit")
        elif "credited" in subject.lower():
            txn = parse_transaction(body, "Credit")
        else:
            continue

        if txn:
            txn["sender"] = sender
            txn["subject"] = subject
            txn["mail_date"] = mail_date
            data_rows.append(txn)

    if not data_rows:
        print("✅ No new transactions found.")
        return

    df = pd.DataFrame(data_rows)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df = df.apply(clean, axis=1)

    # Filter strictly using timestamp
    df = df[df["datetime"] > START_DATETIME]

    df.drop(['account', 'sender', 'subject', 'description', 'mail_date', 'transaction_type'], axis=1, inplace=True)

    # === Filter out existing entries again just in case ===
    engine = create_engine(DB_URL)
    existing_df = pd.read_sql("SELECT datetime, amount, type, id FROM transactions", engine)
    df['datetime'] = pd.to_datetime(df['datetime'])
    existing_df['datetime'] = pd.to_datetime(existing_df['datetime'])

    merge_cols = ["datetime", "amount", "type", "id"]
    df_unique = df.merge(existing_df, on=merge_cols, how="left", indicator=True)
    df_new = df_unique[df_unique["_merge"] == "left_only"].drop(columns=["_merge"])

    if not df_new.empty:
        df_new.to_sql("transactions", engine, if_exists="append", index=False)
        print(f"✅ Uploaded {len(df_new)} new transactions.")
    else:
        print("✅ No new transactions to upload.")

    mail.logout()



if __name__ == "__main__":
    main()
    print(f"⏱️ Script finished in {round(time.time() - start_time, 2)} seconds.")
