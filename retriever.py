from imap_tools import MailBox, AND

from config import IMAP_USER, IMAP_PASSWORD, OUTPUT_DIR, IMAP_HOST, DATE

def retrieve_email():
    # SWElist sends two digests from this address on the same date, in the same
    # minute: "<emoji> N New Internships Posted Today" and "<emoji> N New Jobs
    # Posted Today" (new grad). Sender and date alone match both, so without the
    # subject this returns whichever the server happens to hand back first.
    # The emoji varies day to day; the words don't, and they're disjoint.
    with MailBox(IMAP_HOST).login(IMAP_USER, IMAP_PASSWORD) as mailbox:
        for msg in mailbox.fetch(AND(from_='noreply@swelist.com', date=DATE,
                                     subject='Internships')):
            if 'Internships' not in (msg.subject or ''):
                continue
            OUTPUT_DIR.mkdir(exist_ok=True)
            return msg

if __name__ == "__main__":
    email = retrieve_email()
    print(email.date, email.subject)
    file_path = OUTPUT_DIR / 'full_email.html'
    with file_path.open('w'):
        file_path.write_text(email.html)
    