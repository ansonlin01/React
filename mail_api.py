from flask import Flask, request, jsonify
from bs4 import BeautifulSoup  # 需要安裝 bs4: pip install beautifulsoup4
import json
import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


app = Flask(__name__)

@app.route('/get_emails', methods=['POST'])
def get_emails():
    try:
        # 接收請求數據
        data = request.json
        imap_server = data.get('imap_server', 'imap.gmail.com')
        email_user = data.get('email_user','XXXXyour_mailaddress')
        email_pass = data.get('email_pass','XXXyour_mail password')
        specific_sender = data.get('specific_sender')

        # 驗證參數
        if not all([email_user, email_pass, specific_sender]):
            return jsonify({"error": "Missing required parameters: email_user, email_pass, specific_sender"}), 400

        # 連接到 IMAP 伺服器
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_user, email_pass)
        mail.select("inbox")

        # 搜尋來自特定寄件人的郵件
        search_criteria = f'FROM "{specific_sender}"'
        status, messages = mail.search(None, search_criteria)

        if status != "OK" or not messages[0]:
            return jsonify({"error": f"No emails found from {specific_sender}"}), 404

        # 取得所有符合條件的郵件 ID
        mail_ids = messages[0].split()
        emails = []

        for mail_id in reversed(mail_ids):  # 由最新到最舊
            status, msg_data = mail.fetch(mail_id, '(RFC822)')

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # 解碼郵件主題
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    from_ = msg.get("From")

                    # 處理郵件內容
                    email_content = {
                        "subject": subject,
                        "from": from_,
                        "body": ""
                    }

                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))

                            try:
                                body = part.get_payload(decode=True).decode()
                            except:
                                continue

                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                email_content["body"] = body
                                break
                            elif content_type == "text/html" and "attachment" not in content_disposition:
                                soup = BeautifulSoup(body, "html.parser")
                                text = soup.get_text()
                                email_content["body"] = text
                                break
                    else:
                        content_type = msg.get_content_type()
                        body = msg.get_payload(decode=True).decode()
                        if content_type == "text/plain":
                            email_content["body"] = body
                        elif content_type == "text/html":
                            soup = BeautifulSoup(body, "html.parser")
                            text = soup.get_text()
                            email_content["body"] = text

                    emails.append(email_content)

        # 返回郵件內容
        return jsonify({"emails": emails})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            mail.logout()
        except:
            pass

@app.route('/send_email', methods=['POST'])
def send_email():
    try:
        # 接收請求數據
        data = request.json
        smtp_server = data.get('smtp_server', 'smtp.gmail.com')
        smtp_port = data.get('smtp_port', 587)
        sender_email = data.get('sender_email','XXX@gmail.com')
        receiver_email = data.get('receiver_email')
        password = data.get('password','XXXyour_mailpassword')
        subject = data.get('subject', 'No Subject')
        body = data.get('body', '')

        # 驗證必填參數
        if not all([sender_email, receiver_email, password, body]):
            return jsonify({"error": "Missing required parameters: sender_email, receiver_email, password, body"}), 400

        # 建立 MIMEMultipart 物件
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        # 發送郵件
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # 啟用 TLS 加密
        server.login(sender_email, password)  # 登入帳戶
        server.sendmail(sender_email, receiver_email, message.as_string())  # 發送郵件
        server.quit()  # 關閉連接

        return jsonify({"message": "Email sent successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7474, debug=True)
