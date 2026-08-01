from imap_tools import MailBox, AND

from config import IMAP_USER, IMAP_PASSWORD, OUTPUT_DIR, IMAP_HOST, DATE

def retrieve_email():
    with MailBox(IMAP_HOST).login(IMAP_USER, IMAP_PASSWORD) as mailbox:
        for msg in mailbox.fetch(AND(from_='noreply@swelist.com', date=DATE)):
            OUTPUT_DIR.mkdir(exist_ok=True)
            return msg

if __name__ == "__main__":
    email = retrieve_email()
    print(email.date, email.subject)
    file_path = OUTPUT_DIR / 'full_email.html'
    with file_path.open('w'):
        file_path.write_text(email.html)
    