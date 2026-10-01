from imap_tools import MailBox, AND

from config import IMAP_USER, IMAP_PASSWORD, OUTPUT_DIR, IMAP_HOST, DATE


def retrieve_email():
    # SWElist sends two digests from this address on the same date, in the same
    # minute: "<emoji> N New Internships Posted Today" and "<emoji> N New Jobs
    # Posted Today" (new grad). Sender and date alone match both, so the subject
    # has to be checked client-side to tell them apart.
    #
    # Don't pass subject= to the server-side IMAP search: Gmail's SUBJECT search
    # is word-tokenized, not a substring match, so a fixed search term of either
    # 'Internship' or 'Internships' silently fails to match the other grammatical
    # form (singular subject when there's exactly 1 listing, plural otherwise)
    # and the message never comes back at all. from_ + date alone reliably
    # returns both of today's messages; only the client-side check does the
    # actual substring matching.
    with MailBox(IMAP_HOST).login(IMAP_USER, IMAP_PASSWORD) as mailbox:
        for msg in mailbox.fetch(AND(from_='noreply@swelist.com', date=DATE)):
            if 'Internship' not in (msg.subject or ''):
                continue
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            return msg

    # Fail loudly. Returning None here just moves the crash to the caller as
    # an opaque AttributeError on .date several stages later.
    raise LookupError(
        f"No SWElist message from noreply@swelist.com on {DATE.isoformat()} "
        f"with 'Internship' in the subject. The digest may not have arrived yet."
    )


if __name__ == "__main__":
    email = retrieve_email()
    print(email.date, email.subject)
    file_path = OUTPUT_DIR / 'full_email.html'
    with file_path.open('w'):
        file_path.write_text(email.html)
